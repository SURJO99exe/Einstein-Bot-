/**
 * Deploy Commands Script
 * Registers slash commands with Discord
 * Run this after setting up your .env file
 */

const { REST, Routes } = require('discord.js');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const token = process.env.DISCORD_TOKEN;
const clientId = process.env.CLIENT_ID;
const guildId = process.env.GUILD_ID;

if (!token || !clientId) {
    console.error('❌ Missing required environment variables:');
    if (!token) console.error('   - DISCORD_TOKEN');
    if (!clientId) console.error('   - CLIENT_ID');
    console.error('\nPlease check your .env file and try again.');
    process.exit(1);
}

const commands = [];

// Load commands from all subdirectories
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
            commands.push(command.data.toJSON());
            console.log(`✅ Loaded command: ${command.data.name}`);
        } else {
            console.log(`⚠️ Skipping ${file} - missing required properties`);
        }
    }
}

// Construct and prepare an instance of the REST module
const rest = new REST({ version: '10' }).setToken(token);

// Deploy commands
(async () => {
    try {
        console.log(`\n🚀 Started refreshing ${commands.length} application (/) commands.`);

        let data;
        
        if (guildId) {
            // Guild-specific deployment (faster, for development)
            console.log(`📍 Deploying to guild: ${guildId}`);
            data = await rest.put(
                Routes.applicationGuildCommands(clientId, guildId),
                { body: commands }
            );
        } else {
            // Global deployment (takes up to 1 hour to propagate)
            console.log(`🌍 Deploying globally (this may take up to 1 hour to appear everywhere)`);
            data = await rest.put(
                Routes.applicationCommands(clientId),
                { body: commands }
            );
        }

        console.log(`✅ Successfully reloaded ${data.length} application (/) commands.`);
        console.log('\n📋 Registered commands:');
        data.forEach(cmd => console.log(`   • /${cmd.name} - ${cmd.description}`));
        
    } catch (error) {
        console.error('❌ Error deploying commands:', error);
        
        if (error.status === 401) {
            console.error('\n⚠️ Invalid token. Please check your DISCORD_TOKEN in .env');
        } else if (error.status === 403) {
            console.error('\n⚠️ Permission denied. Make sure your bot has the applications.commands scope.');
        }
    }
})();
