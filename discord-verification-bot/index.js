/**
 * Discord Verification Bot
 * A complete verification system with buttons, captcha, and security features
 * Using discord.js v14
 */

const { Client, GatewayIntentBits, Partials, Collection } = require('discord.js');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Create client with necessary intents
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMessageTyping
    ],
    partials: [Partials.Channel, Partials.Message, Partials.GuildMember]
});

// Store for commands, cooldowns, and pending verifications
client.commands = new Collection();
client.cooldowns = new Collection();
client.pendingVerifications = new Map();
client.verificationAttempts = new Map();

// Load handlers
const handlersPath = path.join(__dirname, 'handlers');
const handlerFiles = fs.readdirSync(handlersPath).filter(file => file.endsWith('.js'));

for (const file of handlerFiles) {
    const filePath = path.join(handlersPath, file);
    const handler = require(filePath);
    if (handler.once) {
        client.once(handler.name, (...args) => handler.execute(...args, client));
    } else {
        client.on(handler.name, (...args) => handler.execute(...args, client));
    }
}

// Load commands
const commandsPath = path.join(__dirname, 'commands');
const commandFolders = fs.readdirSync(commandsPath);

for (const folder of commandFolders) {
    const folderPath = path.join(commandsPath, folder);
    if (!fs.statSync(folderPath).isDirectory()) continue;
    
    const commandFiles = fs.readdirSync(folderPath).filter(file => file.endsWith('.js'));
    for (const file of commandFiles) {
        const filePath = path.join(folderPath, file);
        const command = require(filePath);
        if ('data' in command && 'execute' in command) {
            client.commands.set(command.data.name, command);
        } else {
            console.log(`[WARNING] The command at ${filePath} is missing required properties.`);
        }
    }
}

// Error handling
process.on('unhandledRejection', error => {
    console.error('Unhandled promise rejection:', error);
});

process.on('uncaughtException', error => {
    console.error('Uncaught exception:', error);
});

// Login to Discord
const token = process.env.DISCORD_TOKEN;
if (!token) {
    console.error('ERROR: DISCORD_TOKEN is not set in .env file');
    process.exit(1);
}

client.login(token).then(() => {
    console.log(`✅ Bot logged in successfully!`);
    console.log(`🤖 Bot Name: ${client.user.tag}`);
    console.log(`📅 Started at: ${new Date().toLocaleString()}`);
}).catch(error => {
    console.error('Failed to login:', error);
    process.exit(1);
});
