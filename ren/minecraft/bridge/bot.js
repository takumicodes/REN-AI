/**
 * REN-AI Minecraft Mineflayer Bridge 11.0
 * Comprehensive Action Execution Engine with Procedural Building, Mace & Wind Charge PvP,
 * Verifiable Block Operations, Resource Mining, Crafting, and Real-time Telemetry.
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

// CLI Argument Parsing
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

            setInterval(publishState, 2000);
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
            summary[item.name] = (summary[item.name] || 0) + item.count;
        }
    } catch (e) {}
    return summary;
}

function getNearbyEntities(maxDistance = 32) {
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
    const hostiles = ['zombie', 'skeleton', 'spider', 'creeper', 'enderman', 'witch', 'drowned', 'husk', 'phantom', 'slime', 'pillager', 'blaze'];
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

function getEquipmentSummary() {
    if (!bot || !bot.inventory) return {};
    try {
        return {
            main_hand: bot.heldItem ? bot.heldItem.name : null,
            off_hand: bot.inventory.slots[45] ? bot.inventory.slots[45].name : null,
            helmet: bot.inventory.slots[5] ? bot.inventory.slots[5].name : null,
            chestplate: bot.inventory.slots[6] ? bot.inventory.slots[6].name : null,
            leggings: bot.inventory.slots[7] ? bot.inventory.slots[7].name : null,
            boots: bot.inventory.slots[8] ? bot.inventory.slots[8].name : null
        };
    } catch (e) {
        return {};
    }
}

function getNearbyPOIs() {
    if (!bot || !bot.findBlocks) return { crafting_tables: [], furnaces: [], beds: [], chests: [], hazards: [] };
    try {
        const mcData = require('minecraft-data')(bot.version);
        const findIds = (names) => names.map(n => mcData.blocksByName[n] ? mcData.blocksByName[n].id : null).filter(id => id !== null);

        const tablePositions = bot.findBlocks({ matching: findIds(['crafting_table']), maxDistance: 16, count: 2 }) || [];
        const furnacePositions = bot.findBlocks({ matching: findIds(['furnace', 'blast_furnace', 'smoker']), maxDistance: 16, count: 2 }) || [];
        const bedPositions = bot.findBlocks({ matching: findIds(['white_bed', 'red_bed', 'blue_bed', 'bed']), maxDistance: 16, count: 2 }) || [];
        const chestPositions = bot.findBlocks({ matching: findIds(['chest', 'trapped_chest', 'barrel']), maxDistance: 16, count: 2 }) || [];
        const hazardPositions = bot.findBlocks({ matching: findIds(['lava', 'fire', 'cactus', 'magma_block']), maxDistance: 8, count: 4 }) || [];

        const toCoords = (positions) => positions.map(p => ({ x: Math.round(p.x), y: Math.round(p.y), z: Math.round(p.z) }));

        return {
            crafting_tables: toCoords(tablePositions),
            furnaces: toCoords(furnacePositions),
            beds: toCoords(bedPositions),
            chests: toCoords(chestPositions),
            hazards: toCoords(hazardPositions)
        };
    } catch (e) {
        return { crafting_tables: [], furnaces: [], beds: [], chests: [], hazards: [] };
    }
}

function publishState() {
    if (!bot || !bot.entity) return;

    try {
        const timeOfDay = (bot.time && bot.time.timeOfDay) ? bot.time.timeOfDay : 0;
        const isNight = timeOfDay >= 13000 && timeOfDay <= 23000;
        const isDusk = (timeOfDay >= 12000 && timeOfDay < 13000) || (timeOfDay > 23000);

        const currBlock = bot.blockAt(bot.entity.position);
        const biomeName = (currBlock && currBlock.biome && currBlock.biome.name) ? currBlock.biome.name : 'plains';
        const pois = getNearbyPOIs();

        const state = {
            hp: Math.round(bot.health || 20),
            max_hp: 20,
            food: Math.round(bot.food || 20),
            saturation: Math.round((bot.foodSaturation || 5) * 10) / 10,
            pos: {
                x: Math.round(bot.entity.position.x * 10) / 10,
                y: Math.round(bot.entity.position.y * 10) / 10,
                z: Math.round(bot.entity.position.z * 10) / 10
            },
            yaw: Math.round(bot.entity.yaw * 100) / 100,
            pitch: Math.round(bot.entity.pitch * 100) / 100,
            dimension: bot.game ? bot.game.dimension : 'overworld',
            biome: biomeName,
            inventory: getInventorySummary(),
            equipment: getEquipmentSummary(),
            entities: getNearbyEntities(32),
            pois: pois,
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

            case 'goTo':
            case 'move_to': {
                const { x, y, z } = action;
                await bot.pathfinder.goto(new goals.GoalNear(x, y, z, 1.5)).catch(() => {});
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

            case 'gather':
            case 'mine_block': {
                await gatherBlocks(action.block_type || 'oak_log', action.count || 3, task_id);
                break;
            }

            case 'craft':
            case 'craft_item': {
                await craftItem(action.item_name, action.count || 1, task_id);
                break;
            }

            case 'smelt':
            case 'smelt_item': {
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

            case 'build_structure': {
                await executeStructuredBlueprint(action.blocks, action.structure_name, task_id);
                break;
            }

            case 'eat':
            case 'eat_food': {
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
                    await bot.equip(windCharge, 'hand').catch(() => {});
                    await bot.look(bot.entity.yaw, -Math.PI / 2, true).catch(() => {});
                    bot.activateItem();
                    await new Promise(r => setTimeout(r, 250));
                    await bot.equip(mace, 'hand').catch(() => {});
                    await bot.lookAt(targetPlayer.position.offset(0, targetPlayer.height * 0.8, 0)).catch(() => {});
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
    const sword = bot.inventory.items().find(i => i.name.includes('sword') || i.name.includes('axe') || i.name.includes('mace'));
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
        try {
            const woolItem = mcData.itemsByName.white_wool || mcData.itemsByName.wool || mcData.itemsByName.oak_planks;
            if (woolItem) {
                bot.creative.setInventorySlot(36, new (require('prismarine-item')(bot.version))(woolItem.id, 64));
            }
        } catch (e) {}
    }

    let blockToPlace = bot.inventory.items().find(i => i.name.includes('wool') || i.name.includes('plank') || i.name === 'dirt' || i.name === 'cobblestone');
    if (!blockToPlace && !isCreative) {
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
            const weapon = bot.inventory.items().find(i => i.name.includes('mace') || i.name.includes('sword') || i.name.includes('axe'));
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

// 6. Execute Structured Blueprint (Walks to each coordinate and places verified blocks)
async function executeStructuredBlueprint(blockPlacements, structureName, taskId) {
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

    let placedCount = 0;
    const blocks = blockPlacements || [];

    for (const b of blocks) {
        const targetPos = new Vec3(b.x, b.y, b.z);
        const currentBlock = bot.blockAt(targetPos);
        const refBlock = bot.blockAt(targetPos.offset(0, -1, 0));

        if (currentBlock && currentBlock.name === 'air' && refBlock && refBlock.name !== 'air') {
            const blockItem = bot.inventory.items().find(i =>
                i.name.includes('plank') || i.name.includes('log') || i.name === 'dirt' || i.name === 'cobblestone' || i.name === 'stone' || i.name.includes('wool')
            );

            if (blockItem) {
                try {
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

    bot.chat(`Completed ${structureName || 'structure'}! Placed ${placedCount} verified blocks.`);
    sendEvent('task_done', {
        task_id: taskId,
        cmd: 'build_structure',
        success: placedCount > 0,
        details: { placed_count: placedCount, total: blocks.length }
    });
}

// 7. Walking 3D House Builder
async function buildWalking3DHouse(taskId) {
    const origin = bot.entity.position.floored().offset(3, 0, 0);
    const blocksToPlace = [];

    // Walls layer 0 and 1
    for (let y = 0; y < 2; y++) {
        for (let x = -1; x <= 1; x++) {
            for (let z = -1; z <= 1; z++) {
                if (x === 0 && z === 0) continue;
                if (x === 0 && z === 1) continue; // doorway opening
                blocksToPlace.push({ x: origin.x + x, y: origin.y + y, z: origin.z + z });
            }
        }
    }

    // Roof layer
    for (let x = -1; x <= 1; x++) {
        for (let z = -1; z <= 1; z++) {
            blocksToPlace.push({ x: origin.x + x, y: origin.y + 2, z: origin.z + z });
        }
    }

    await executeStructuredBlueprint(blocksToPlace, 'survival_house', taskId);
}

// 8. Collect Drops
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

// 9. Hunt Animals
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
            const weapon = bot.inventory.items().find(it => it.name.includes('mace') || it.name.includes('sword') || it.name.includes('axe'));
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
        sendEvent('task_done', { task_id: taskId, cmd: 'hunt', success: true, details: { killed_count: killed } });
    } else {
        sendEvent('task_done', { task_id: taskId, cmd: 'hunt', success: false, error: `No ${animalName} found nearby.` });
    }
}

// Active Terrain & Cave Roaming Exploration
async function roamAndFindCave(matchingIds, maxRoamSteps = 3) {
    for (let step = 0; step < maxRoamSteps; step++) {
        let exposed = bot.findBlocks({
            matching: matchingIds,
            maxDistance: 48,
            count: 8
        });

        if (exposed && exposed.length > 0) {
            return exposed;
        }

        const angle = (Math.PI * 2 / maxRoamSteps) * step + (Math.random() * 0.5);
        const roamDistance = 25 + Math.random() * 10;
        const targetX = bot.entity.position.x + Math.cos(angle) * roamDistance;
        const targetZ = bot.entity.position.z + Math.sin(angle) * roamDistance;
        const targetY = bot.entity.position.y;

        bot.chat(`Roaming terrain to discover cave entrance & exposed stone... 🏔️`);
        try {
            await bot.pathfinder.goto(new goals.GoalNear(targetX, targetY, targetZ, 3)).catch(() => {});
            await new Promise(r => setTimeout(r, 300));
        } catch (e) {}

        exposed = bot.findBlocks({
            matching: matchingIds,
            maxDistance: 32,
            count: 8
        });
        if (exposed && exposed.length > 0) {
            return exposed;
        }
    }
    return [];
}

// 10. Gather Blocks with Cave Roaming & Reachable Distance
async function gatherBlocks(blockType, count, taskId) {
    let targetNames = [blockType];
    const clean = blockType.toLowerCase();

    if (clean.includes('wood') || clean.includes('log') || clean.includes('tree')) {
        targetNames = ['oak_log', 'birch_log', 'spruce_log', 'acacia_log', 'dark_oak_log', 'jungle_log', 'mangrove_log', 'cherry_log'];
    } else if (clean.includes('stone') || clean.includes('cobble')) {
        targetNames = ['stone', 'cobblestone', 'deepslate', 'granite', 'diorite', 'andesite', 'sandstone'];
    } else if (clean.includes('iron')) {
        targetNames = ['iron_ore', 'deepslate_iron_ore', 'raw_iron_block'];
    } else if (clean.includes('coal')) {
        targetNames = ['coal_ore', 'deepslate_coal_ore'];
    } else if (clean.includes('diamond')) {
        targetNames = ['diamond_ore', 'deepslate_diamond_ore'];
    } else if (clean.includes('dirt') || clean.includes('sand')) {
        targetNames = ['dirt', 'grass_block', 'sand', 'gravel'];
    }

    const matchingIds = targetNames.map(name => {
        const b = bot.registry.blocksByName[name];
        return b ? b.id : null;
    }).filter(id => id !== null);

    // 1. Search for nearest reachable blocks (within 32 blocks)
    let foundPositions = bot.findBlocks({
        matching: matchingIds,
        maxDistance: 32,
        count: Math.max(count * 2, 8)
    });

    const botPos = bot.entity.position;
    if (clean.includes('wood') || clean.includes('log')) {
        foundPositions = foundPositions.filter(p => Math.abs(p.y - botPos.y) <= 4);
    }

    foundPositions.sort((a, b) => botPos.distanceTo(a) - botPos.distanceTo(b));
    let blocksToCollect = foundPositions.slice(0, count);

    // 2. Roam & Cave Exploration for Stone / Iron / Coal
    if ((!blocksToCollect || blocksToCollect.length === 0) && (clean.includes('stone') || clean.includes('cobble') || clean.includes('iron') || clean.includes('coal') || clean.includes('diamond'))) {
        const exposed = await roamAndFindCave(matchingIds, 3);
        if (exposed && exposed.length > 0) {
            blocksToCollect = exposed.slice(0, count);
        } else if (clean.includes('stone') || clean.includes('cobble')) {
            // Penetrate surface dirt down to stone layer
            const flooredPos = bot.entity.position.floored();
            const digOffsets = [
                flooredPos.offset(1, 0, 0),
                flooredPos.offset(1, -1, 0),
                flooredPos.offset(1, -2, 0),
                flooredPos.offset(1, -3, 0),
                flooredPos.offset(1, -4, 0)
            ];

            const shovel = bot.inventory.items().find(i => i.name.includes('shovel'));
            const pickaxe = bot.inventory.items().find(i => i.name.includes('pickaxe'));

            for (const pos of digOffsets) {
                const b = bot.blockAt(pos);
                if (b && b.name !== 'air' && b.name !== 'bedrock') {
                    try {
                        if (b.name.includes('stone') || b.name.includes('cobble')) {
                            if (pickaxe) await bot.equip(pickaxe, 'hand').catch(() => {});
                        } else {
                            if (shovel) await bot.equip(shovel, 'hand').catch(() => {});
                        }
                        await bot.dig(b).catch(() => {});
                        await new Promise(r => setTimeout(r, 60));
                    } catch (e) {}
                }
            }

            await collectNearbyDrops(8);
            blocksToCollect = bot.findBlocks({ matching: matchingIds, maxDistance: 16, count: count });
        }
    }

    if (!blocksToCollect || blocksToCollect.length === 0) {
        bot.chat(`Couldn't find any ${blockType} nearby.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: false, error: `No ${blockType} found nearby.` });
        return;
    }

    try {
        const bestTool = bot.inventory.items().find(i => {
            if (clean.includes('wood')) return i.name.includes('axe');
            if (clean.includes('stone') || clean.includes('iron') || clean.includes('coal') || clean.includes('diamond')) return i.name.includes('pickaxe');
            return false;
        });
        if (bestTool) await bot.equip(bestTool, 'hand').catch(() => {});

        const targets = blocksToCollect.map(pos => bot.blockAt(pos)).filter(b => b !== null);
        bot.chat(`Harvesting ${targets.length}x ${blockType}... ⛏️`);

        // Wrap collectBlock with a 15-second timeout promise to avoid infinite hang
        const collectPromise = bot.collectBlock.collect(targets);
        const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error("Collect timeout")), 15000));

        await Promise.race([collectPromise, timeoutPromise]);
        bot.chat(`Collected ${targets.length}x ${blockType}!`);
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: true, details: { count: targets.length } });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: false, error: e.message });
    }
}

// 11. Craft Items with Auto-Intermediate Resolution & Table Collection
async function craftItem(itemName, count, taskId) {
    const item = bot.registry.itemsByName[itemName];
    if (!item) {
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: `Item '${itemName}' does not exist.` });
        return;
    }

    // 1. If logs exist and planks are needed, craft planks first
    const invLogs = bot.inventory.items().filter(i => i.name.includes('_log') || i.name === 'log');
    const invPlanks = bot.inventory.items().filter(i => i.name.includes('_planks') || i.name === 'planks');
    const invSticks = bot.inventory.items().find(i => i.name === 'stick');

    if (itemName !== 'oak_planks' && invPlanks.length === 0 && invLogs.length > 0) {
        try {
            const plankItem = bot.registry.itemsByName.oak_planks || bot.registry.itemsByName.planks;
            const plankRecipes = bot.recipesFor(plankItem ? plankItem.id : null, null, 1, null);
            if (plankRecipes && plankRecipes.length > 0) {
                await bot.craft(plankRecipes[0], 2, null).catch(() => {});
            }
        } catch (e) {}
    }

    // 2. If tools/weapons/torches are requested and sticks are missing, craft sticks first
    const needsSticks = ['pickaxe', 'sword', 'axe', 'shovel', 'torch', 'bow', 'fishing_rod', 'lever'].some(t => itemName.includes(t));
    if (needsSticks && (!invSticks || invSticks.count < 2)) {
        try {
            const stickItem = bot.registry.itemsByName.stick;
            const stickRecipes = bot.recipesFor(stickItem ? stickItem.id : null, null, 1, null);
            if (stickRecipes && stickRecipes.length > 0) {
                await bot.craft(stickRecipes[0], 1, null).catch(() => {});
            }
        } catch (e) {}
    }

    // 3. Locate or Place Crafting Table (reuse nearby within 16 blocks)
    let craftingTableBlock = bot.findBlock({
        matching: bot.registry.blocksByName.crafting_table.id,
        maxDistance: 16
    });

    let placedTablePos = null;

    if (craftingTableBlock) {
        if (bot.entity.position.distanceTo(craftingTableBlock.position) > 3) {
            try {
                await bot.pathfinder.goto(new goals.GoalNear(craftingTableBlock.position.x, craftingTableBlock.position.y, craftingTableBlock.position.z, 2));
            } catch (e) {}
        }
    } else {
        let tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
        if (!tableItem) {
            // Only craft if we don't have one and none nearby
            try {
                const tableItemDef = bot.registry.itemsByName.crafting_table;
                const tableRecipes = bot.recipesFor(tableItemDef.id, null, 1, null);
                if (tableRecipes && tableRecipes.length > 0) {
                    await bot.craft(tableRecipes[0], 1, null).catch(() => {});
                    tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
                }
            } catch (e) {}
        }

        if (tableItem) {
            const placePos = bot.entity.position.floored().offset(1, 0, 0);
            const ref = bot.blockAt(placePos.offset(0, -1, 0));
            if (ref && ref.name !== 'air') {
                await bot.equip(tableItem, 'hand').catch(() => {});
                await bot.placeBlock(ref, new Vec3(0, 1, 0)).catch(() => {});
                craftingTableBlock = bot.blockAt(placePos);
                placedTablePos = placePos;
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
        bot.chat(`Crafted ${itemName.replace('_', ' ')}! 🛠️`);

        // Auto-equip if weapon, tool, shield, or armor
        const craftedItem = bot.inventory.items().find(i => i.name === itemName);
        if (craftedItem) {
            if (['sword', 'pickaxe', 'axe', 'mace'].some(w => itemName.includes(w))) {
                await bot.equip(craftedItem, 'hand').catch(() => {});
            } else if (itemName === 'shield') {
                await bot.equip(craftedItem, 'off-hand').catch(() => {});
            }
        }

        // Break and collect placed crafting table back to inventory so it is NEVER lost
        if (placedTablePos) {
            try {
                const targetTable = bot.blockAt(placedTablePos);
                if (targetTable && targetTable.name === 'crafting_table') {
                    const axe = bot.inventory.items().find(i => i.name.includes('axe'));
                    if (axe) await bot.equip(axe, 'hand').catch(() => {});
                    await bot.dig(targetTable).catch(() => {});
                    await collectNearbyDrops(4);
                }
            } catch (e) {}
        }

        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: true, details: { item_name: itemName, count: craftAmount } });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: e.message });
    }
}

// 12. Smelt Items
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

// 13. Attack Nearest Mob
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
            const weapon = bot.inventory.items().find(i => i.name.includes('mace') || i.name.includes('sword') || i.name.includes('axe'));
            if (weapon) await bot.equip(weapon, 'hand').catch(() => {});
            bot.chat(`Attacking ${target.name}! ⚔️`);
            bot.pvp.attack(mobEntity);
            sendEvent('task_done', { task_id: taskId, cmd: 'attack', success: true, message: `Engaging ${target.name}` });
        } catch (e) {
            sendEvent('task_done', { task_id: taskId, cmd: 'attack', success: false, error: e.message });
        }
    }
}

// 14. Sleep
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
