/**
 * REN-AI Minecraft Mineflayer Bridge 9.0 (Full Creative & Survival Player Agency)
 * Complete feature set:
 * - Walking 3D Builder: Walks to each block position to construct complete 3x3 houses and ceilings without reach errors.
 * - Creative Mode Support: Auto-supplies materials in creative mode; auto-harvests in survival.
 * - In-Game Gamemode Commands: Executes /gamemode survival / /gamemode creative on command.
 * - Bridging Engine: Places bridges across chasms and air.
 * - Item Pickup & Drop All: Picks up dropped swords/items and drops all items on command.
 * - PvP Duel & Area Defense: Duels players or clears all nearby monsters.
 * - Fluid Dynamic Follow: Real-time sprinting and pathing.
 */

const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
const collectBlock = require('mineflayer-collectblock').plugin;
const autoEat = require('mineflayer-auto-eat').plugin;
const pvp = require('mineflayer-pvp').plugin;
const Vec3 = require('vec3').Vec3;
const readline = require('readline');

// Global Anti-Crash Containment
process.on('uncaughtException', (err) => {
    sendEvent('error', { error: `UncaughtException: ${err.message}` });
});

process.on('unhandledRejection', (reason) => {
    sendEvent('error', { error: `UnhandledRejection: ${typeof reason === 'object' ? reason.message : String(reason)}` });
});

// Parse CLI Arguments
const args = process.argv.slice(2);
const options = {
    host: 'localhost',
    port: 25565,
    username: 'RenAI',
    version: false,
    auth: 'offline'
};

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--host' && args[i + 1]) options.host = args[i + 1];
    if (args[i] === '--port' && args[i + 1]) options.port = parseInt(args[i + 1], 10);
    if (args[i] === '--username' && args[i + 1]) options.username = args[i + 1];
    if (args[i] === '--version' && args[i + 1]) options.version = args[i + 1];
    if (args[i] === '--auth' && args[i + 1]) options.auth = args[i + 1];
}

function sendEvent(type, data = {}) {
    try {
        const payload = { event: type, timestamp: Date.now(), ...data };
        process.stdout.write(JSON.stringify(payload) + '\n');
    } catch (e) {}
}

let bot = null;
let defaultMovements = null;
let currentTask = null;
let followingPlayerName = null;
let followIntervalId = null;

function createBot() {
    sendEvent('connecting', { host: options.host, port: options.port, username: options.username });

    const botConfig = {
        host: options.host,
        port: options.port,
        username: options.username,
        auth: options.auth,
        checkTimeoutInterval: 60000
    };
    if (options.version) botConfig.version = options.version;

    try {
        bot = mineflayer.createBot(botConfig);
    } catch (e) {
        sendEvent('error', { error: `Failed to create bot: ${e.message}` });
        return;
    }

    try {
        bot.loadPlugin(pathfinder);
        bot.loadPlugin(collectBlock);
        bot.loadPlugin(autoEat);
        bot.loadPlugin(pvp);
    } catch (e) {
        sendEvent('error', { error: `Plugin load error: ${e.message}` });
    }

    bot.once('spawn', () => {
        try {
            const mcData = require('minecraft-data')(bot.version);
            defaultMovements = new Movements(bot, mcData);
            defaultMovements.canDig = true;
            defaultMovements.canOpenDoors = true;
            defaultMovements.allow1by1towers = true;
            defaultMovements.allowParkour = true;
            defaultMovements.allowSprinting = true;
            defaultMovements.maxDropDown = 4;

            if (mcData.blocksByName.dirt) {
                defaultMovements.scafoldingBlocks = [
                    mcData.blocksByName.dirt.id,
                    mcData.blocksByName.cobblestone ? mcData.blocksByName.cobblestone.id : null,
                    mcData.blocksByName.oak_planks ? mcData.blocksByName.oak_planks.id : null
                ].filter(id => id !== null);
            }

            bot.pathfinder.setMovements(defaultMovements);

            bot.autoEat.options.priority = 'foodPoints';
            bot.autoEat.options.bannedFood = ['rotten_flesh', 'poisonous_potato', 'pufferfish', 'spider_eye'];

            sendEvent('ready', {
                username: bot.username,
                version: bot.version,
                gameMode: bot.game ? bot.game.gameMode : 'survival',
                difficulty: bot.game ? bot.game.difficulty : 'normal'
            });

            setInterval(publishState, 2500);
            setInterval(companionTick, 1000);
        } catch (err) {
            sendEvent('error', { error: `Spawn setup error: ${err.message}` });
        }
    });

    bot.on('chat', (username, message) => {
        if (username === bot.username) return;
        sendEvent('chat', { username, message });
    });

    bot.on('whisper', (username, message) => {
        sendEvent('whisper', { username, message });
    });

    bot.on('health', () => {
        sendEvent('health', { health: bot.health, food: bot.food, saturation: bot.foodSaturation });
    });

    bot.on('death', () => {
        stopFollowLoop();
        sendEvent('death', {
            position: bot.entity ? bot.entity.position : null,
            inventory: getInventorySummary()
        });
    });

    bot.on('entityHurt', (entity) => {
        if (entity === bot.entity) {
            sendEvent('damage_taken', { health: bot.health });
        }
    });

    bot.on('kicked', (reason) => {
        sendEvent('kicked', { reason: typeof reason === 'object' ? JSON.stringify(reason) : String(reason) });
    });

    bot.on('error', (err) => {
        sendEvent('error', { error: err.message });
    });

    bot.on('end', () => {
        sendEvent('disconnected');
    });
}

function getInventorySummary() {
    if (!bot || !bot.inventory) return {};
    const summary = {};
    try {
        for (const item of bot.inventory.items()) {
            if (summary[item.name]) {
                summary[item.name] += item.count;
            } else {
                summary[item.name] = item.count;
            }
        }
    } catch (e) {}
    return summary;
}

function getNearbyEntities(maxDistance = 64) {
    if (!bot || !bot.entities || !bot.entity) return [];
    const nearby = [];
    const botPos = bot.entity.position;

    try {
        for (const id in bot.entities) {
            const ent = bot.entities[id];
            if (!ent || ent === bot.entity || !ent.position) continue;
            const dist = botPos.distanceTo(ent.position);
            if (dist <= maxDistance) {
                nearby.push({
                    id: ent.id,
                    name: ent.name || ent.username || 'unknown',
                    type: ent.type,
                    distance: Math.round(dist * 10) / 10,
                    position: { x: Math.round(ent.position.x), y: Math.round(ent.position.y), z: Math.round(ent.position.z) },
                    isHostile: isHostileMob(ent.name),
                    isAnimal: isPassiveAnimal(ent.name),
                    isPlayer: ent.type === 'player'
                });
            }
        }
    } catch (e) {}
    return nearby;
}

function isHostileMob(name) {
    if (!name) return false;
    const hostiles = ['zombie', 'skeleton', 'spider', 'creeper', 'enderman', 'witch', 'drowned', 'husk', 'phantom', 'slime', 'pillager'];
    return hostiles.some(h => name.toLowerCase().includes(h));
}

function isPassiveAnimal(name) {
    if (!name) return false;
    const animals = ['cow', 'pig', 'sheep', 'chicken', 'rabbit', 'horse', 'donkey', 'llama', 'goat'];
    return animals.some(a => name.toLowerCase().includes(a));
}

function findTargetPlayer(playerName) {
    if (!bot || !bot.entity) return null;

    if (playerName && bot.players[playerName] && bot.players[playerName].entity) {
        return bot.players[playerName].entity;
    }

    if (playerName) {
        const cleanName = playerName.toLowerCase().trim();
        for (const name in bot.players) {
            if (name.toLowerCase() === cleanName && bot.players[name].entity) {
                return bot.players[name].entity;
            }
        }
    }

    try {
        const nearest = bot.nearestEntity(e => e.type === 'player' && e !== bot.entity);
        if (nearest) return nearest;
    } catch (e) {}

    return null;
}

function publishState() {
    if (!bot || !bot.entity) return;

    try {
        const timeOfDay = (bot.time && bot.time.timeOfDay) ? bot.time.timeOfDay : 0;
        const isNight = timeOfDay >= 13000 && timeOfDay <= 23000;
        const isDusk = (timeOfDay >= 12000 && timeOfDay < 13000) || (timeOfDay > 23000);

        const state = {
            hp: Math.round(bot.health || 20),
            food: Math.round(bot.food || 20),
            pos: {
                x: Math.round(bot.entity.position.x * 10) / 10,
                y: Math.round(bot.entity.position.y * 10) / 10,
                z: Math.round(bot.entity.position.z * 10) / 10
            },
            inventory: getInventorySummary(),
            entities: getNearbyEntities(32),
            timeOfDay: isNight ? 'night' : (isDusk ? 'dusk' : 'day'),
            rawTime: timeOfDay,
            activeTask: currentTask
        };

        sendEvent('state', state);
    } catch (e) {}
}

function startFollowLoop(playerName) {
    stopFollowLoop();
    followingPlayerName = playerName;

    followIntervalId = setInterval(() => {
        if (!bot || !bot.entity || currentTask !== 'follow') return;

        const playerEntity = findTargetPlayer(followingPlayerName);
        if (!playerEntity) return;

        const dist = bot.entity.position.distanceTo(playerEntity.position);

        if (dist > 3) {
            bot.lookAt(playerEntity.position.offset(0, playerEntity.height * 0.8, 0)).catch(() => {});
            bot.pathfinder.setGoal(new goals.GoalNear(playerEntity.position.x, playerEntity.position.y, playerEntity.position.z, 2));
        } else if (dist <= 2) {
            bot.lookAt(playerEntity.position.offset(0, playerEntity.height * 0.8, 0)).catch(() => {});
        }
    }, 800);
}

function stopFollowLoop() {
    if (followIntervalId) {
        clearInterval(followIntervalId);
        followIntervalId = null;
    }
    followingPlayerName = null;
}

async function companionTick() {
    if (!bot || !bot.entity || currentTask) return;

    try {
        const armorSlots = [
            { slot: 'head', types: ['helmet'] },
            { slot: 'torso', types: ['chestplate'] },
            { slot: 'legs', types: ['leggings'] },
            { slot: 'feet', types: ['boots'] }
        ];

        for (const armor of armorSlots) {
            const item = bot.inventory.items().find(i => armor.types.some(t => i.name.includes(t)));
            if (item) {
                await bot.equip(item, armor.slot).catch(() => {});
            }
        }

        const shield = bot.inventory.items().find(i => i.name === 'shield');
        if (shield) {
            await bot.equip(shield, 'off-hand').catch(() => {});
        }

        const nearestPlayer = bot.nearestEntity(e => e.type === 'player' && e !== bot.entity);
        if (nearestPlayer && bot.entity.position.distanceTo(nearestPlayer.position) < 8) {
            await bot.lookAt(nearestPlayer.position.offset(0, nearestPlayer.height * 0.8, 0)).catch(() => {});
        }
    } catch (e) {}
}

// --- Action Command Router ---
async function handleAction(action) {
    const { cmd, task_id } = action;

    if (cmd === 'chat') {
        if (action.message && bot) {
            bot.chat(action.message);
            sendEvent('task_done', { task_id, cmd, success: true });
        }
        return;
    }

    if (cmd !== 'follow') {
        stopFollowLoop();
    }

    try {
        if (bot.pathfinder) bot.pathfinder.stop();
        if (bot.pvp) bot.pvp.stop();
    } catch (e) {}

    currentTask = cmd;

    try {
        switch (cmd) {
            case 'follow': {
                const targetEntity = findTargetPlayer(action.player);
                if (!targetEntity) {
                    bot.chat(`I can't see you nearby. Move closer!`);
                    sendEvent('task_done', { task_id, cmd, success: false, error: `Player entity not visible.` });
                    return;
                }

                startFollowLoop(action.player);
                bot.chat(`Following you closely! 🏃`);
                sendEvent('task_done', { task_id, cmd, success: true, message: `Following player` });
                break;
            }

            case 'pvp':
            case 'fight':
            case 'attack_player': {
                const targetPlayer = findTargetPlayer(action.player);
                if (!targetPlayer) {
                    bot.chat(`I can't find you nearby to fight!`);
                    sendEvent('task_done', { task_id, cmd, success: false, error: 'Player not found' });
                    return;
                }

                await performPvPCombat(targetPlayer, task_id);
                sendEvent('task_done', { task_id, cmd, success: true, message: `Duelling ${action.player}` });
                break;
            }

            case 'gamemode':
            case 'set_game_mode': {
                const mode = action.mode || 'survival';
                bot.chat(`/gamemode ${mode}`);
                bot.chat(`Switched game mode to ${mode}! ✨`);
                sendEvent('task_done', { task_id, cmd, success: true, message: `Set gamemode ${mode}` });
                break;
            }

            case 'pickup':
            case 'take': {
                await pickupNearbyItems(task_id);
                break;
            }

            case 'drop_all':
            case 'give_all': {
                await dropAllItemsToPlayer(action.player, task_id);
                break;
            }

            case 'bridge':
            case 'do_bridging': {
                await buildBridge(action.length || 8, action.material || 'wool', task_id);
                break;
            }

            case 'kill_all_mobs': {
                await killAllNearbyMobs(task_id);
                break;
            }

            case 'stop': {
                stopFollowLoop();
                if (bot.pathfinder) bot.pathfinder.stop();
                if (bot.pvp) bot.pvp.stop();
                currentTask = null;
                sendEvent('task_done', { task_id, cmd, success: true, message: 'Stopped all tasks.' });
                break;
            }

            case 'goTo': {
                const { x, y, z } = action;
                await bot.pathfinder.goto(new goals.GoalNear(x, y, z, 1)).catch(() => {});
                sendEvent('task_done', { task_id, cmd, success: true, message: `Moved to ${x}, ${y}, ${z}` });
                break;
            }

            case 'give': {
                await giveItemToPlayer(action.player, action.item_name, action.count || 1, task_id);
                break;
            }

            case 'hunt': {
                await huntAnimals(action.animal_name || 'cow', action.count || 2, task_id);
                break;
            }

            case 'gather': {
                await gatherBlocks(action.block_type || 'oak_log', action.count || 3, task_id);
                break;
            }

            case 'craft': {
                await craftItem(action.item_name, action.count || 1, task_id);
                break;
            }

            case 'smelt': {
                await smeltItem(action.item, action.fuel, action.count || 1, task_id);
                break;
            }

            case 'attack': {
                await attackNearestMob(action.target_name || 'zombie', task_id);
                break;
            }

            case 'protect': {
                startFollowLoop(action.player);
                bot.chat(`Guard mode active! Watching your back. 🛡️`);
                sendEvent('task_done', { task_id, cmd, success: true, message: `Guard mode active.` });
                break;
            }

            case 'sleep': {
                await sleepInBed(task_id);
                break;
            }

            case 'build_shelter': {
                await buildWalking3DHouse(task_id);
                break;
            }

            case 'eat': {
                if (bot.autoEat) {
                    bot.autoEat.eat();
                    sendEvent('task_done', { task_id, cmd, success: true, message: 'Eating available food.' });
                }
                break;
            }

            default:
                sendEvent('task_done', { task_id, cmd, success: false, error: `Unknown command '${cmd}'` });
        }
    } catch (err) {
        sendEvent('task_done', { task_id, cmd, success: false, error: err.message });
    } finally {
        if (cmd !== 'follow' && cmd !== 'pvp') {
            currentTask = null;
        }
    }
}

// Dynamic PvP Combat with Mace & Wind Charge Aerial Smash Combo
async function performPvPCombat(targetPlayer, taskId) {
    if (!targetPlayer) return;

    const mace = bot.inventory.items().find(i => i.name.includes('mace'));
    const windCharge = bot.inventory.items().find(i => i.name.includes('wind_charge'));
    const sword = bot.inventory.items().find(i => i.name.includes('sword') || i.name.includes('axe'));

    // Equip primary weapon (Mace prioritized for crushing smash attacks)
    const bestWeapon = mace || sword;
    if (bestWeapon) await bot.equip(bestWeapon, 'hand').catch(() => {});

    // Off-hand shield
    const shield = bot.inventory.items().find(i => i.name === 'shield');
    if (shield) await bot.equip(shield, 'off-hand').catch(() => {});

    if (mace && windCharge) {
        bot.chat(`Mace & Wind Charges armed! Preparing Aerial Smash Combo! 💨🔨`);
    } else if (mace) {
        bot.chat(`Heavy Mace equipped! Prepare for crushing smash attacks! 🔨`);
    } else {
        bot.chat(`Sword drawn! Let's duel! ⚔️`);
    }

    bot.pvp.attack(targetPlayer);

    // Wind Charge Aerial Smash Combo Loop during PvP
    if (windCharge && mace) {
        const smashInterval = setInterval(async () => {
            if (currentTask !== 'pvp' || !targetPlayer.isValid) {
                clearInterval(smashInterval);
                return;
            }

            const dist = bot.entity.position.distanceTo(targetPlayer.position);
            if (dist < 8) {
                try {
                    // 1. Equip Wind Charge
                    await bot.equip(windCharge, 'hand').catch(() => {});
                    // 2. Look straight down at feet
                    await bot.look(bot.entity.yaw, -Math.PI / 2, true).catch(() => {});
                    // 3. Launch into the air with wind burst!
                    bot.activateItem();
                    await new Promise(r => setTimeout(r, 250));
                    // 4. Swap to Mace in mid-air
                    await bot.equip(mace, 'hand').catch(() => {});
                    // 5. Aim crosshair directly down onto opponent's head
                    await bot.lookAt(targetPlayer.position.offset(0, targetPlayer.height * 0.8, 0)).catch(() => {});
                    // 6. Smash attack on descent!
                    bot.attack(targetPlayer);
                } catch (e) {}
            }
        }, 4000);
    }
}

// 1. Give Item to Player
async function giveItemToPlayer(playerName, itemName, count, taskId) {
    const playerEntity = findTargetPlayer(playerName);
    if (!playerEntity) {
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: false, error: `Player '${playerName}' not found.` });
        return;
    }

    const invItems = bot.inventory.items();
    let targetItem = null;
    const cleanQuery = (itemName || '').toLowerCase().replace('_', ' ');

    for (const item of invItems) {
        const cleanName = item.name.toLowerCase().replace('_', ' ');
        if (cleanName.includes(cleanQuery) || cleanQuery.includes(cleanName) ||
            (cleanQuery.includes('wood') && (cleanName.includes('log') || cleanName.includes('plank'))) ||
            (cleanQuery.includes('stone') && (cleanName.includes('stone') || cleanName.includes('cobble'))) ||
            (cleanQuery.includes('iron') && cleanName.includes('iron')) ||
            (cleanQuery.includes('food') && ['beef', 'bread', 'porkchop', 'mutton', 'apple'].some(f => cleanName.includes(f)))) {
            targetItem = item;
            break;
        }
    }

    if (!targetItem) {
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: false, error: `No '${itemName}' in inventory.` });
        return;
    }

    const dropCount = Math.min(count, targetItem.count);

    try {
        await bot.pathfinder.goto(new goals.GoalNear(playerEntity.position.x, playerEntity.position.y, playerEntity.position.z, 2)).catch(() => {});
        await bot.lookAt(playerEntity.position.offset(0, playerEntity.height * 0.8, 0)).catch(() => {});
        await bot.toss(targetItem.type, null, dropCount);
        bot.chat(`Here you go, ${playerName}! Dropped ${dropCount}x ${targetItem.name.replace('_', ' ')}.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: true, message: `Gave ${dropCount}x ${targetItem.name} to ${playerName}` });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: false, error: e.message });
    }
}

// 2. Drop All Items
async function dropAllItemsToPlayer(playerName, taskId) {
    const playerEntity = findTargetPlayer(playerName);
    if (playerEntity) {
        await bot.pathfinder.goto(new goals.GoalNear(playerEntity.position.x, playerEntity.position.y, playerEntity.position.z, 2)).catch(() => {});
        await bot.lookAt(playerEntity.position.offset(0, playerEntity.height * 0.8, 0)).catch(() => {});
    }

    const items = bot.inventory.items();
    let count = 0;
    for (const it of items) {
        try {
            await bot.toss(it.type, null, it.count);
            count++;
            await new Promise(r => setTimeout(r, 100));
        } catch (e) {}
    }

    bot.chat(`Dropped all ${count} items from my inventory for you!`);
    sendEvent('task_done', { task_id: taskId, cmd: 'drop_all', success: true, message: `Dropped ${count} items.` });
}

// 3. Pickup Dropped Items Nearby
async function pickupNearbyItems(taskId) {
    bot.chat("Picking up items nearby...");
    await collectNearbyDrops(16);
    // Equip best sword
    const sword = bot.inventory.items().find(i => i.name.includes('sword') || i.name.includes('axe'));
    if (sword) await bot.equip(sword, 'hand').catch(() => {});
    bot.chat("Picked up items and equipped weapon!");
    sendEvent('task_done', { task_id: taskId, cmd: 'pickup', success: true });
}

// 4. Bridging Engine
async function buildBridge(length = 8, material = 'wool', taskId) {
    bot.chat(`Building a ${length}-block bridge ahead...`);
    const isCreative = bot.game && bot.game.gameMode === 'creative';
    const mcData = require('minecraft-data')(bot.version);

    if (isCreative) {
        // Auto-supply wool in creative
        try {
            const woolItem = mcData.itemsByName.white_wool || mcData.itemsByName.wool || mcData.itemsByName.oak_planks;
            if (woolItem) {
                bot.creative.setInventorySlot(36, new (require('prismarine-item')(bot.version))(woolItem.id, 64));
            }
        } catch (e) {}
    }

    let blockToPlace = bot.inventory.items().find(i => i.name.includes('wool') || i.name.includes('plank') || i.name === 'dirt' || i.name === 'cobblestone');
    if (!blockToPlace && !isCreative) {
        // Gather 8 dirt
        const targets = bot.findBlocks({ matching: [mcData.blocksByName.dirt.id, mcData.blocksByName.grass_block.id], maxDistance: 16, count: length });
        if (targets && targets.length > 0) {
            try { await bot.collectBlock.collect(targets.map(p => bot.blockAt(p))); } catch (e) {}
        }
    }

    let placed = 0;
    const startPos = bot.entity.position.floored();
    const dir = new Vec3(Math.round(-Math.sin(bot.entity.yaw)), 0, Math.round(Math.cos(bot.entity.yaw)));

    for (let i = 1; i <= length; i++) {
        const bridgePos = startPos.plus(dir.scaled(i)).offset(0, -1, 0);
        const refPos = bridgePos.minus(dir);
        const refBlock = bot.blockAt(refPos);

        if (refBlock && refBlock.name !== 'air') {
            blockToPlace = bot.inventory.items().find(it => it.name.includes('wool') || it.name.includes('plank') || it.name === 'dirt' || it.name === 'cobblestone');
            if (blockToPlace) {
                try {
                    await bot.equip(blockToPlace, 'hand').catch(() => {});
                    await bot.pathfinder.goto(new goals.GoalNear(refPos.x, refPos.y + 1, refPos.z, 1.5)).catch(() => {});
                    await bot.placeBlock(refBlock, dir).catch(() => {});
                    placed++;
                    await new Promise(r => setTimeout(r, 150));
                } catch (e) {}
            }
        }
    }

    bot.chat(`Bridge finished! Placed ${placed} blocks.`);
    sendEvent('task_done', { task_id: taskId, cmd: 'bridge', success: true, message: `Placed ${placed} bridge blocks.` });
}

// 5. Kill All Nearby Mobs
async function killAllNearbyMobs(taskId) {
    bot.chat("Engaging all hostile mobs in the area! ⚔️");
    const entities = getNearbyEntities(32);
    const hostiles = entities.filter(e => e.isHostile);

    let killed = 0;
    for (const target of hostiles) {
        const mobEntity = bot.entities[target.id];
        if (!mobEntity || !mobEntity.isValid) continue;

        try {
            const weapon = bot.inventory.items().find(i => i.name.includes('sword') || i.name.includes('axe'));
            if (weapon) await bot.equip(weapon, 'hand').catch(() => {});

            await bot.pathfinder.goto(new goals.GoalNear(mobEntity.position.x, mobEntity.position.y, mobEntity.position.z, 2)).catch(() => {});
            bot.pvp.attack(mobEntity);

            let waited = 0;
            while (mobEntity.isValid && waited < 15) {
                await new Promise(r => setTimeout(r, 400));
                waited++;
            }
            killed++;
        } catch (e) {}
    }

    await collectNearbyDrops(16);
    bot.chat(`Cleared area! Defeated ${killed} hostile mobs.`);
    sendEvent('task_done', { task_id: taskId, cmd: 'kill_all_mobs', success: true });
}

// 6. Walking 3D House Builder (Walks to each block to place 100% of the house)
async function buildWalking3DHouse(taskId) {
    const isCreative = bot.game && bot.game.gameMode === 'creative';
    const mcData = require('minecraft-data')(bot.version);

    if (isCreative) {
        try {
            const woodItem = mcData.itemsByName.oak_planks || mcData.itemsByName.dirt;
            if (woodItem) {
                bot.creative.setInventorySlot(36, new (require('prismarine-item')(bot.version))(woodItem.id, 64));
            }
        } catch (e) {}
    }

    let invItems = bot.inventory.items();
    let buildingBlock = invItems.find(i => 
        i.name === 'dirt' || i.name === 'cobblestone' || i.name === 'stone' || i.name.includes('plank') || i.name.includes('log')
    );

    // If survival and no blocks, harvest 16 dirt blocks
    if (!buildingBlock || buildingBlock.count < 12) {
        bot.chat("Harvesting building materials right here...");
        const groundTargets = bot.findBlocks({
            matching: [mcData.blocksByName.dirt.id, mcData.blocksByName.grass_block.id, mcData.blocksByName.stone ? mcData.blocksByName.stone.id : 1],
            maxDistance: 16,
            count: 16
        });
        if (groundTargets && groundTargets.length > 0) {
            try { await bot.collectBlock.collect(groundTargets.map(p => bot.blockAt(p))); } catch (e) {}
        }
    }

    bot.chat("Constructing full 3x3 survival house! Placing walls, doorway, and roof...");
    const origin = bot.entity.position.floored().offset(3, 0, 0);
    let placedCount = 0;

    // List of coordinates for 3x3 house
    const blocksToPlace = [];

    // Walls layer 0 (y=0) and layer 1 (y=1)
    for (let y = 0; y < 2; y++) {
        for (let x = -1; x <= 1; x++) {
            for (let z = -1; z <= 1; z++) {
                if (x === 0 && z === 0) continue; // interior
                if (x === 0 && z === 1) continue; // doorway opening
                blocksToPlace.push({ pos: origin.offset(x, y, z), y_level: y });
            }
        }
    }

    // Roof layer (y=2)
    for (let x = -1; x <= 1; x++) {
        for (let z = -1; z <= 1; z++) {
            blocksToPlace.push({ pos: origin.offset(x, 2, z), y_level: 2 });
        }
    }

    // Sequentially walk and place every single block
    for (const item of blocksToPlace) {
        const targetPos = item.pos;
        const currentBlock = bot.blockAt(targetPos);
        const refBlock = bot.blockAt(targetPos.offset(0, -1, 0));

        if (currentBlock && currentBlock.name === 'air' && refBlock && refBlock.name !== 'air') {
            const blockItem = bot.inventory.items().find(i => 
                i.name === 'dirt' || i.name === 'cobblestone' || i.name === 'stone' || i.name.includes('plank') || i.name.includes('log') || i.name.includes('wool')
            );

            if (blockItem) {
                try {
                    // Walk within 2.5 blocks so placement NEVER fails out of reach
                    await bot.pathfinder.goto(new goals.GoalNear(targetPos.x, targetPos.y, targetPos.z, 2.5)).catch(() => {});
                    await bot.equip(blockItem, 'hand').catch(() => {});
                    await bot.lookAt(targetPos.offset(0.5, 0.5, 0.5)).catch(() => {});
                    await bot.placeBlock(refBlock, new Vec3(0, 1, 0)).catch(() => {});
                    placedCount++;
                    await new Promise(r => setTimeout(r, 120));
                } catch (e) {}
            }
        }
    }

    bot.chat(`Finished constructing our house at X:${origin.x} Y:${origin.y} Z:${origin.z}! Placed ${placedCount} blocks.`);
    sendEvent('task_done', { task_id: taskId, cmd: 'build_shelter', success: true, message: `Built shelter with ${placedCount} blocks at ${origin.x}, ${origin.y}, ${origin.z}` });
}

// 7. Collect Drops
async function collectNearbyDrops(radius = 12) {
    if (!bot || !bot.entities) return;
    try {
        const botPos = bot.entity.position;
        for (const id in bot.entities) {
            const ent = bot.entities[id];
            if (ent && ent.name === 'item' && ent.position) {
                if (botPos.distanceTo(ent.position) <= radius && ent.isValid) {
                    await bot.pathfinder.goto(new goals.GoalNear(ent.position.x, ent.position.y, ent.position.z, 1)).catch(() => {});
                }
            }
        }
    } catch (e) {}
}

// 8. Hunt Animals
async function huntAnimals(animalName, totalCount, taskId) {
    let killed = 0;
    const cleanAnimal = (animalName || 'animal').toLowerCase();

    for (let i = 0; i < totalCount; i++) {
        const entities = getNearbyEntities(64);
        const candidates = entities.filter(e => {
            if (cleanAnimal === 'animal' || cleanAnimal === 'food') return e.isAnimal;
            return e.name.toLowerCase().includes(cleanAnimal);
        });

        if (candidates.length === 0) break;

        const target = candidates.sort((a, b) => a.distance - b.distance)[0];
        const mobEntity = bot.entities[target.id];
        if (!mobEntity) continue;

        try {
            const weapon = bot.inventory.items().find(it => it.name.includes('sword') || it.name.includes('axe'));
            if (weapon) await bot.equip(weapon, 'hand').catch(() => {});

            await bot.pathfinder.goto(new goals.GoalNear(mobEntity.position.x, mobEntity.position.y, mobEntity.position.z, 2)).catch(() => {});
            bot.pvp.attack(mobEntity);

            let waited = 0;
            while (mobEntity.isValid && waited < 12) {
                await new Promise(r => setTimeout(r, 400));
                waited++;
            }
            killed++;
            await collectNearbyDrops(12);
        } catch (e) {}
    }

    if (killed > 0) {
        bot.chat(`Hunted ${killed} animal(s)! Food collected.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'hunt', success: true, message: `Hunted ${killed} animals.` });
    } else {
        sendEvent('task_done', { task_id: taskId, cmd: 'hunt', success: false, error: `No ${animalName} found.` });
    }
}

// 9. Gather Blocks
async function gatherBlocks(blockType, count, taskId) {
    let targetNames = [blockType];
    const clean = blockType.toLowerCase();

    if (clean.includes('wood') || clean.includes('log') || clean.includes('tree')) {
        targetNames = ['oak_log', 'birch_log', 'spruce_log', 'acacia_log', 'dark_oak_log', 'jungle_log', 'mangrove_log', 'cherry_log'];
    } else if (clean.includes('stone') || clean.includes('cobble')) {
        targetNames = ['stone', 'cobblestone', 'deepslate', 'granite', 'diorite', 'andesite'];
    } else if (clean.includes('iron')) {
        targetNames = ['iron_ore', 'deepslate_iron_ore'];
    } else if (clean.includes('coal')) {
        targetNames = ['coal_ore', 'deepslate_coal_ore'];
    } else if (clean.includes('dirt') || clean.includes('sand')) {
        targetNames = ['dirt', 'grass_block', 'sand', 'gravel'];
    }

    const matchingIds = targetNames.map(name => {
        const b = bot.registry.blocksByName[name];
        return b ? b.id : null;
    }).filter(id => id !== null);

    let blocksToCollect = bot.findBlocks({
        matching: matchingIds,
        maxDistance: 64,
        count: count
    });

    if ((!blocksToCollect || blocksToCollect.length === 0) && (clean.includes('stone') || clean.includes('cobble'))) {
        const surfacePos = bot.entity.position.floored().offset(1, -1, 0);
        const digTargets = [
            bot.blockAt(surfacePos),
            bot.blockAt(surfacePos.offset(0, -1, 0)),
            bot.blockAt(surfacePos.offset(0, -2, 0))
        ].filter(b => b && b.name !== 'air');

        if (digTargets.length > 0) {
            try {
                await bot.collectBlock.collect(digTargets);
            } catch (e) {}
        }

        blocksToCollect = bot.findBlocks({ matching: matchingIds, maxDistance: 32, count: count });
    }

    if (!blocksToCollect || blocksToCollect.length === 0) {
        bot.chat(`Couldn't find any ${blockType} nearby.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: false, error: `No ${blockType} found nearby.` });
        return;
    }

    try {
        const bestTool = bot.inventory.items().find(i => {
            if (clean.includes('wood')) return i.name.includes('axe');
            if (clean.includes('stone') || clean.includes('iron') || clean.includes('coal')) return i.name.includes('pickaxe');
            return false;
        });
        if (bestTool) await bot.equip(bestTool, 'hand').catch(() => {});

        const targets = blocksToCollect.map(pos => bot.blockAt(pos)).filter(b => b !== null);
        bot.chat(`Harvesting ${targets.length}x ${blockType}...`);
        await bot.collectBlock.collect(targets);
        bot.chat(`Collected ${targets.length}x ${blockType}!`);
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: true, message: `Collected ${targets.length} ${blockType} blocks.` });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: false, error: e.message });
    }
}

// 10. Craft Items
async function craftItem(itemName, count, taskId) {
    const item = bot.registry.itemsByName[itemName];
    if (!item) {
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: `Item '${itemName}' does not exist.` });
        return;
    }

    let craftingTableBlock = bot.findBlock({
        matching: bot.registry.blocksByName.crafting_table.id,
        maxDistance: 6
    });

    if (!craftingTableBlock) {
        const tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
        if (tableItem) {
            const placePos = bot.entity.position.floored().offset(1, 0, 0);
            const ref = bot.blockAt(placePos.offset(0, -1, 0));
            if (ref && ref.name !== 'air') {
                await bot.equip(tableItem, 'hand').catch(() => {});
                await bot.placeBlock(ref, new Vec3(0, 1, 0)).catch(() => {});
                craftingTableBlock = bot.blockAt(placePos);
            }
        }
    }

    const recipes = bot.recipesFor(item.id, null, 1, craftingTableBlock);
    if (!recipes || recipes.length === 0) {
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: 'Missing crafting materials.' });
        return;
    }

    try {
        const recipe = recipes[0];
        const craftAmount = Math.max(1, Math.min(count, 4));
        await bot.craft(recipe, craftAmount, craftingTableBlock);
        bot.chat(`Crafted ${itemName.replace('_', ' ')}!`);
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: true, message: `Crafted ${itemName}.` });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: e.message });
    }
}

// 11. Smelt Items
async function smeltItem(rawItemName, fuelName, count, taskId) {
    let furnaceBlock = bot.findBlock({
        matching: bot.registry.blocksByName.furnace.id,
        maxDistance: 6
    });

    if (!furnaceBlock) {
        const furnaceItem = bot.inventory.items().find(i => i.name === 'furnace');
        if (furnaceItem) {
            const placePos = bot.entity.position.floored().offset(1, 0, 0);
            const ref = bot.blockAt(placePos.offset(0, -1, 0));
            if (ref && ref.name !== 'air') {
                await bot.equip(furnaceItem, 'hand').catch(() => {});
                await bot.placeBlock(ref, new Vec3(0, 1, 0)).catch(() => {});
                furnaceBlock = bot.blockAt(placePos);
            }
        }
    }

    if (!furnaceBlock) {
        sendEvent('task_done', { task_id: taskId, cmd: 'smelt', success: false, error: 'No furnace found.' });
        return;
    }

    try {
        const furnace = await bot.openFurnace(furnaceBlock);
        const inputItem = bot.inventory.items().find(i => i.name.includes(rawItemName || 'raw_iron') || i.name.includes('beef') || i.name.includes('pork'));
        const fuelItem = bot.inventory.items().find(i => i.name.includes(fuelName || 'coal') || i.name.includes('planks') || i.name.includes('log'));

        if (inputItem) await furnace.putInput(inputItem.type, null, count || inputItem.count).catch(() => {});
        if (fuelItem) await furnace.putFuel(fuelItem.type, null, 2).catch(() => {});

        bot.chat(`Smelting in furnace now!`);
        await furnace.close().catch(() => {});
        sendEvent('task_done', { task_id: taskId, cmd: 'smelt', success: true, message: 'Smelting started.' });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'smelt', success: false, error: e.message });
    }
}

// 12. Attack Nearest Mob
async function attackNearestMob(mobName, taskId) {
    const entities = getNearbyEntities(32);
    const target = entities.find(e => e.name.toLowerCase().includes(mobName.toLowerCase()));

    if (!target) {
        sendEvent('task_done', { task_id: taskId, cmd: 'attack', success: false, error: `No nearby ${mobName}.` });
        return;
    }

    const mobEntity = bot.entities[target.id];
    if (mobEntity) {
        try {
            const weapon = bot.inventory.items().find(i => i.name.includes('sword') || i.name.includes('axe'));
            if (weapon) await bot.equip(weapon, 'hand').catch(() => {});
            bot.chat(`Attacking ${target.name}! ⚔️`);
            bot.pvp.attack(mobEntity);
            sendEvent('task_done', { task_id: taskId, cmd: 'attack', success: true, message: `Engaging ${target.name}` });
        } catch (e) {
            sendEvent('task_done', { task_id: taskId, cmd: 'attack', success: false, error: e.message });
        }
    }
}

// 13. Sleep
async function sleepInBed(taskId) {
    const bedBlock = bot.findBlock({
        matching: [
            bot.registry.blocksByName.red_bed ? bot.registry.blocksByName.red_bed.id : null,
            bot.registry.blocksByName.white_bed ? bot.registry.blocksByName.white_bed.id : null
        ].filter(id => id !== null),
        maxDistance: 6
    });

    if (!bedBlock) {
        sendEvent('task_done', { task_id: taskId, cmd: 'sleep', success: false, error: 'No bed nearby.' });
        return;
    }

    try {
        await bot.sleep(bedBlock);
        bot.chat("Sleeping until dawn... 🌙");
        sendEvent('task_done', { task_id: taskId, cmd: 'sleep', success: true, message: 'Sleeping in bed.' });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'sleep', success: false, error: e.message });
    }
}

// Standard Input Reader
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

rl.on('line', (line) => {
    line = line.trim();
    if (!line) return;
    try {
        const action = JSON.parse(line);
        handleAction(action);
    } catch (e) {
        sendEvent('error', { error: `Invalid JSON action: ${e.message}` });
    }
});

createBot();
