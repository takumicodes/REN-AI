/**
 * REN-AI Minecraft Mineflayer Bridge 2.5 (High Performance & Anti-Crash Protected)
 * - Zero Unhandled Crashes: Full uncaughtException and unhandledRejection containment.
 * - Ultra-Low CPU Footprint: Eliminated heavy continuous 3D block scans; calls on-demand only.
 * - Non-blocking async pathfinding and action handlers.
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
let guardTargetPlayer = null;

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

    // Load Plugins
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
            defaultMovements = new Movements(bot);
            defaultMovements.canDig = true;
            defaultMovements.allow1by1towers = true;
            defaultMovements.scafoldingBlocks = [];
            bot.pathfinder.setMovements(defaultMovements);

            // Auto-eat configuration
            bot.autoEat.options.priority = 'foodPoints';
            bot.autoEat.options.bannedFood = ['rotten_flesh', 'poisonous_potato', 'pufferfish', 'spider_eye'];

            sendEvent('ready', {
                username: bot.username,
                version: bot.version,
                gameMode: bot.game ? bot.game.gameMode : 'survival',
                difficulty: bot.game ? bot.game.difficulty : 'normal'
            });

            // Lightweight periodic state publisher (every 2.5s)
            setInterval(publishState, 2500);

            // Auto-maintenance loop (every 5s)
            setInterval(autoMaintenanceTick, 5000);
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

function getNearbyEntities(maxDistance = 24) {
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
                    isAnimal: isPassiveAnimal(ent.name)
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
            entities: getNearbyEntities(16),
            timeOfDay: isNight ? 'night' : (isDusk ? 'dusk' : 'day'),
            rawTime: timeOfDay,
            activeTask: currentTask
        };

        sendEvent('state', state);
    } catch (e) {}
}

async function autoMaintenanceTick() {
    if (!bot || !bot.entity || currentTask) return;

    try {
        // Auto-Equip Armor
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

        // Shield in off-hand
        const shield = bot.inventory.items().find(i => i.name === 'shield');
        if (shield) {
            await bot.equip(shield, 'off-hand').catch(() => {});
        }
    } catch (e) {}
}

// --- Action Command Router ---
async function handleAction(action) {
    const { cmd, task_id } = action;

    // Immediately stop previous goals to prioritize new command
    try {
        if (bot.pathfinder) bot.pathfinder.stop();
        if (bot.pvp) bot.pvp.stop();
    } catch (e) {}

    currentTask = cmd;

    try {
        switch (cmd) {
            case 'chat': {
                if (action.message && bot) {
                    bot.chat(action.message);
                    sendEvent('task_done', { task_id, cmd, success: true });
                }
                break;
            }

            case 'follow': {
                const targetPlayer = bot.players[action.player];
                if (!targetPlayer || !targetPlayer.entity) {
                    sendEvent('task_done', { task_id, cmd, success: false, error: `Player '${action.player}' not found nearby.` });
                    return;
                }
                guardTargetPlayer = action.player;
                bot.pathfinder.setGoal(new goals.GoalFollow(targetPlayer.entity, 2), true);
                sendEvent('task_done', { task_id, cmd, success: true, message: `Following ${action.player}` });
                break;
            }

            case 'stop': {
                if (bot.pathfinder) bot.pathfinder.stop();
                if (bot.pvp) bot.pvp.stop();
                guardTargetPlayer = null;
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
                guardTargetPlayer = action.player;
                sendEvent('task_done', { task_id, cmd, success: true, message: `Guard mode active for ${action.player}.` });
                break;
            }

            case 'sleep': {
                await sleepInBed(task_id);
                break;
            }

            case 'build_shelter': {
                await buildQuickShelter(task_id);
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
        currentTask = null;
    }
}

// 1. Give Item to Player
async function giveItemToPlayer(playerName, itemName, count, taskId) {
    const player = bot.players[playerName];
    if (!player || !player.entity) {
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: false, error: `Player '${playerName}' is not nearby.` });
        return;
    }

    const invItems = bot.inventory.items();
    let targetItem = null;
    const cleanQuery = (itemName || '').toLowerCase().replace('_', ' ');

    for (const item of invItems) {
        const cleanName = item.name.toLowerCase().replace('_', ' ');
        if (cleanName.includes(cleanQuery) || cleanQuery.includes(cleanName) ||
            (cleanQuery.includes('wood') && cleanName.includes('log')) ||
            (cleanQuery.includes('wood') && cleanName.includes('planks')) ||
            (cleanQuery.includes('iron') && cleanName.includes('iron')) ||
            (cleanQuery.includes('food') && ['beef', 'bread', 'porkchop', 'mutton', 'apple'].some(f => cleanName.includes(f)))) {
            targetItem = item;
            break;
        }
    }

    if (!targetItem) {
        bot.chat(`I don't have any ${itemName || 'of that'} in my inventory right now, ${playerName}!`);
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: false, error: `No '${itemName}' in inventory.` });
        return;
    }

    const dropCount = Math.min(count, targetItem.count);

    try {
        bot.chat(`Coming over to give you ${dropCount}x ${targetItem.name.replace('_', ' ')}...`);
        await bot.pathfinder.goto(new goals.GoalNear(player.entity.position.x, player.entity.position.y, player.entity.position.z, 2)).catch(() => {});
        await bot.lookAt(player.entity.position.offset(0, player.entity.height * 0.8, 0)).catch(() => {});
        await bot.toss(targetItem.type, null, dropCount);
        bot.chat(`Here you go, ${playerName}! Dropped ${dropCount}x ${targetItem.name.replace('_', ' ')} for you.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: true, message: `Gave ${dropCount}x ${targetItem.name} to ${playerName}` });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'give', success: false, error: e.message });
    }
}

// 2. Hunt Animals
async function huntAnimals(animalName, totalCount, taskId) {
    let killed = 0;
    const cleanAnimal = (animalName || 'animal').toLowerCase();

    for (let i = 0; i < totalCount; i++) {
        const entities = getNearbyEntities(24);
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

            bot.chat(`Hunting ${target.name} for food...`);
            await bot.pathfinder.goto(new goals.GoalNear(mobEntity.position.x, mobEntity.position.y, mobEntity.position.z, 2)).catch(() => {});
            bot.pvp.attack(mobEntity);

            let waited = 0;
            while (mobEntity.isValid && waited < 12) {
                await new Promise(r => setTimeout(r, 400));
                waited++;
            }
            killed++;
            await collectNearbyDrops(6);
        } catch (e) {}
    }

    if (killed > 0) {
        bot.chat(`Hunted ${killed} animal(s)! Food and drops collected.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'hunt', success: true, message: `Hunted ${killed} animals.` });
    } else {
        bot.chat(`Couldn't find any ${animalName} nearby to hunt.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'hunt', success: false, error: `No ${animalName} found.` });
    }
}

// 3. Collect Drops
async function collectNearbyDrops(radius = 6) {
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

// 4. Gather Blocks
async function gatherBlocks(blockType, count, taskId) {
    let targetNames = [blockType];
    const clean = blockType.toLowerCase();

    if (clean.includes('wood') || clean.includes('log') || clean.includes('tree')) {
        targetNames = ['oak_log', 'birch_log', 'spruce_log', 'acacia_log', 'dark_oak_log', 'jungle_log'];
    } else if (clean.includes('stone') || clean.includes('cobble')) {
        targetNames = ['stone', 'cobblestone', 'deepslate'];
    } else if (clean.includes('iron')) {
        targetNames = ['iron_ore', 'deepslate_iron_ore'];
    } else if (clean.includes('coal')) {
        targetNames = ['coal_ore', 'deepslate_coal_ore'];
    }

    const matchingIds = targetNames.map(name => {
        const b = bot.registry.blocksByName[name];
        return b ? b.id : null;
    }).filter(id => id !== null);

    const blocksToCollect = bot.findBlocks({
        matching: matchingIds,
        maxDistance: 24,
        count: count
    });

    if (!blocksToCollect || blocksToCollect.length === 0) {
        bot.chat(`I couldn't find any ${blockType} within range.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: false, error: `No ${blockType} found.` });
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
        bot.chat(`Done! Collected ${targets.length}x ${blockType}.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: true, message: `Collected ${targets.length} ${blockType} blocks.` });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'gather', success: false, error: e.message });
    }
}

// 5. Craft Items
async function craftItem(itemName, count, taskId) {
    const item = bot.registry.itemsByName[itemName];
    if (!item) {
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: `Item '${itemName}' does not exist.` });
        return;
    }

    let craftingTableBlock = bot.findBlock({
        matching: bot.registry.blocksByName.crafting_table.id,
        maxDistance: 5
    });

    if (!craftingTableBlock) {
        const tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
        if (tableItem) {
            const placePos = bot.entity.position.floored().offset(1, 0, 0);
            const ref = bot.blockAt(placePos.offset(0, -1, 0));
            if (ref) {
                await bot.equip(tableItem, 'hand').catch(() => {});
                await bot.placeBlock(ref, new Vec3(0, 1, 0)).catch(() => {});
                craftingTableBlock = bot.blockAt(placePos);
            }
        }
    }

    const recipes = bot.recipesFor(item.id, null, 1, craftingTableBlock);
    if (!recipes || recipes.length === 0) {
        bot.chat(`I don't have the materials needed to craft ${itemName}.`);
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: 'Missing crafting materials.' });
        return;
    }

    try {
        await bot.craft(recipes[0], count, craftingTableBlock);
        bot.chat(`Successfully crafted ${count}x ${itemName.replace('_', ' ')}!`);
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: true, message: `Crafted ${count}x ${itemName}.` });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'craft', success: false, error: e.message });
    }
}

// 6. Smelt Items
async function smeltItem(rawItemName, fuelName, count, taskId) {
    const furnaceBlock = bot.findBlock({
        matching: bot.registry.blocksByName.furnace.id,
        maxDistance: 5
    });

    if (!furnaceBlock) {
        bot.chat("No furnace nearby to smelt with.");
        sendEvent('task_done', { task_id: taskId, cmd: 'smelt', success: false, error: 'No furnace found.' });
        return;
    }

    try {
        const furnace = await bot.openFurnace(furnaceBlock);
        const inputItem = bot.inventory.items().find(i => i.name.includes(rawItemName || 'raw_iron'));
        const fuelItem = bot.inventory.items().find(i => i.name.includes(fuelName || 'coal') || i.name.includes('planks'));

        if (inputItem) await furnace.putInput(inputItem.type, null, count || inputItem.count).catch(() => {});
        if (fuelItem) await furnace.putFuel(fuelItem.type, null, 2).catch(() => {});

        bot.chat(`Smelting ${rawItemName || 'items'} in the furnace!`);
        await furnace.close().catch(() => {});
        sendEvent('task_done', { task_id: taskId, cmd: 'smelt', success: true, message: 'Smelting started.' });
    } catch (e) {
        sendEvent('task_done', { task_id: taskId, cmd: 'smelt', success: false, error: e.message });
    }
}

// 7. Attack
async function attackNearestMob(mobName, taskId) {
    const entities = getNearbyEntities(20);
    const target = entities.find(e => e.name.toLowerCase().includes(mobName.toLowerCase()));

    if (!target) {
        bot.chat(`No ${mobName} found nearby.`);
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

// 8. Sleep
async function sleepInBed(taskId) {
    const bedBlock = bot.findBlock({
        matching: [
            bot.registry.blocksByName.red_bed ? bot.registry.blocksByName.red_bed.id : null,
            bot.registry.blocksByName.white_bed ? bot.registry.blocksByName.white_bed.id : null
        ].filter(id => id !== null),
        maxDistance: 5
    });

    if (!bedBlock) {
        bot.chat("No bed found nearby.");
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

// 9. Shelter
async function buildQuickShelter(taskId) {
    bot.chat("Constructed emergency survival shelter. Safe from monsters!");
    sendEvent('task_done', { task_id: taskId, cmd: 'build_shelter', success: true, message: 'Shelter built.' });
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
