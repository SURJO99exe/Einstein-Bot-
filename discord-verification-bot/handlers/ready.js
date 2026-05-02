/**
 * Ready Event Handler
 * Triggered when the bot successfully logs in
 */

const { ActivityType } = require('discord.js');
const { validateConfig } = require('../config');

module.exports = {
    name: 'ready',
    once: true,
    async execute(client) {
        // Validate configuration
        validateConfig();
        
        console.log(`🤖 ${client.user.tag} is now online!`);
        console.log(`📊 Serving ${client.guilds.cache.size} server(s)`);
        
        // Set bot activity
        client.user.setActivity({
            name: 'verification requests | /setupverify',
            type: ActivityType.Watching
        });
        
        // Setup verification channel if it doesn't exist
        await setupVerificationSystem(client);
        
        // Start auto-kick cleanup interval
        startAutoKickChecker(client);
        
        // Start data cleanup interval
        startDataCleanup(client);
        
        console.log('✅ Bot is fully operational!');
    }
};

async function setupVerificationSystem(client) {
    const { config } = require('../config');
    
    try {
        const guild = await client.guilds.fetch(config.guildId);
        if (!guild) {
            console.error('❌ Could not find the configured guild');
            return;
        }
        
        // Check if verification channel exists
        const verifyChannel = await guild.channels.fetch(config.verifyChannelId).catch(() => null);
        if (!verifyChannel) {
            console.error('⚠️ Verification channel not found. Please run /setupverify command to set up the verification system.');
            return;
        }
        
        // Check if verified role exists
        const verifiedRole = await guild.roles.fetch(config.verifiedRoleId).catch(() => null);
        if (!verifiedRole) {
            console.error('⚠️ Verified role not found. Please check your VERIFIED_ROLE_ID in .env');
            return;
        }
        
        console.log(`✅ Verification system ready`);
        console.log(`   📍 Channel: #${verifyChannel.name}`);
        console.log(`   🎭 Role: @${verifiedRole.name}`);
        console.log(`   🔒 Captcha: ${config.enableCaptcha ? 'Enabled' : 'Disabled'}`);
        
    } catch (error) {
        console.error('❌ Error setting up verification system:', error.message);
    }
}

function startAutoKickChecker(client) {
    const { config } = require('../config');
    
    if (config.autoKickMinutes <= 0) return;
    
    setInterval(async () => {
        const now = Date.now();
        const kickTime = config.autoKickMinutes * 60 * 1000;
        
        for (const [guildId, members] of client.pendingVerifications) {
            const guild = client.guilds.cache.get(guildId);
            if (!guild) continue;
            
            for (const [memberId, data] of members) {
                if (now - data.joinTime > kickTime) {
                    try {
                        const member = await guild.members.fetch(memberId).catch(() => null);
                        if (member && !member.roles.cache.has(config.verifiedRoleId)) {
                            await member.send({
                                content: config.messages.kickedMessage.replace('{server}', guild.name)
                            }).catch(() => {});
                            
                            await member.kick('Failed to verify within required time');
                            
                            // Log the kick
                            logEvent(client, guild, 'Auto-Kick', member.user, 'Failed to verify within ' + config.autoKickMinutes + ' minutes');
                        }
                    } catch (error) {
                        console.error('Error auto-kicking member:', error);
                    }
                }
            }
        }
    }, 60000); // Check every minute
    
    console.log(`⏰ Auto-kick enabled: ${config.autoKickMinutes} minutes`);
}

function startDataCleanup(client) {
    const { config } = require('../config');
    
    setInterval(() => {
        const now = Date.now();
        const expiry = config.security.verificationExpiry;
        
        // Clean up old verification attempts
        for (const [userId, data] of client.verificationAttempts) {
            if (now - data.lastAttempt > expiry) {
                client.verificationAttempts.delete(userId);
            }
        }
        
        // Clean up old pending verifications
        for (const [guildId, members] of client.pendingVerifications) {
            for (const [memberId, data] of members) {
                if (now - data.joinTime > expiry) {
                    members.delete(memberId);
                }
            }
            if (members.size === 0) {
                client.pendingVerifications.delete(guildId);
            }
        }
    }, config.security.cleanupInterval);
    
    console.log('🧹 Data cleanup system started');
}

async function logEvent(client, guild, action, user, reason = '') {
    const { config } = require('../config');
    
    if (!config.logChannelId) return;
    
    try {
        const logChannel = await guild.channels.fetch(config.logChannelId).catch(() => null);
        if (!logChannel) return;
        
        const { EmbedBuilder } = require('discord.js');
        const embed = new EmbedBuilder()
            .setTitle(`📋 Verification ${action}`)
            .setColor(action.includes('Failed') || action.includes('Kick') ? config.colors.error : config.colors.success)
            .addFields(
                { name: 'User', value: `${user.tag} (${user.id})`, inline: true },
                { name: 'Action', value: action, inline: true },
                { name: 'Time', value: `<t:${Math.floor(Date.now() / 1000)}:F>`, inline: false }
            )
            .setThumbnail(user.displayAvatarURL({ dynamic: true }))
            .setFooter({ text: `User ID: ${user.id}` })
            .setTimestamp();
        
        if (reason) {
            embed.addFields({ name: 'Reason/Details', value: reason, inline: false });
        }
        
        await logChannel.send({ embeds: [embed] });
    } catch (error) {
        console.error('Error logging event:', error);
    }
}

module.exports.logEvent = logEvent;
