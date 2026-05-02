/**
 * Settings Command
 * View and manage bot settings
 */

const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { EmbedBuilder } = require('discord.js');
const { config } = require('../../config');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('settings')
        .setDescription('View current verification bot settings')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

    async execute(interaction, client) {
        // Check if user has admin permissions
        if (!interaction.memberPermissions.has(PermissionFlagsBits.Administrator)) {
            return await interaction.reply({
                content: '❌ You need Administrator permission to use this command.',
                ephemeral: true
            });
        }

        try {
            const guild = interaction.guild;
            
            // Fetch configured roles and channels
            const verifiedRole = await guild.roles.fetch(config.verifiedRoleId).catch(() => null);
            const unverifiedRole = config.unverifiedRoleId ? await guild.roles.fetch(config.unverifiedRoleId).catch(() => null) : null;
            const verifyChannel = config.verifyChannelId ? await guild.channels.fetch(config.verifyChannelId).catch(() => null) : null;
            const logChannel = config.logChannelId ? await guild.channels.fetch(config.logChannelId).catch(() => null) : null;
            
            // Count pending verifications
            const pendingCount = client.pendingVerifications.get(guild.id)?.size || 0;
            
            // Count cooldowns
            const cooldownCount = client.cooldowns.size;
            
            // Create settings embed
            const settingsEmbed = new EmbedBuilder()
                .setTitle('⚙️ Verification Bot Settings')
                .setDescription('Current configuration and status of the verification system.')
                .setColor(config.colors.info)
                .addFields(
                    { 
                        name: '🎭 Roles Configuration', 
                        value: [
                            `**Verified Role:** ${verifiedRole || '❌ Not found'}`,
                            `**Unverified Role:** ${unverifiedRole || '⚪ Not configured'}`
                        ].join('\n'),
                        inline: false 
                    },
                    { 
                        name: '📍 Channels Configuration', 
                        value: [
                            `**Verify Channel:** ${verifyChannel || '❌ Not found'}`,
                            `**Log Channel:** ${logChannel || '⚪ Not configured'}`
                        ].join('\n'),
                        inline: false 
                    },
                    { 
                        name: '🔒 Security Settings', 
                        value: [
                            `**Captcha:** ${config.enableCaptcha ? '✅ Enabled' : '❌ Disabled'}`,
                            `**Cooldown:** ${config.verificationCooldown} seconds`,
                            `**Max Attempts:** ${config.security.maxAttempts}`,
                            `**Block Duration:** ${config.security.blockDuration / 60000} minutes`
                        ].join('\n'),
                        inline: true 
                    },
                    { 
                        name: '⏰ Auto Features', 
                        value: [
                            `**Auto-Kick:** ${config.autoKickMinutes > 0 ? `✅ ${config.autoKickMinutes} min` : '❌ Disabled'}`,
                            `**Data Expiry:** ${config.security.verificationExpiry / 3600000} hours`
                        ].join('\n'),
                        inline: true 
                    },
                    { 
                        name: '📊 Current Statistics', 
                        value: [
                            `**Pending Verifications:** ${pendingCount} users`,
                            `**Active Cooldowns:** ${cooldownCount} users`,
                            `**Total Guild Members:** ${guild.memberCount}`
                        ].join('\n'),
                        inline: false 
                    }
                )
                .setFooter({ text: `Requested by ${interaction.user.tag}` })
                .setTimestamp();

            // Add bot status
            settingsEmbed.addFields({
                name: '🤖 Bot Status',
                value: [
                    `**Status:** ✅ Online`,
                    `**Uptime:** ${formatUptime(client.uptime)}`,
                    `**Ping:** ${client.ws.ping}ms`
                ].join('\n'),
                inline: false
            });

            await interaction.reply({
                embeds: [settingsEmbed],
                ephemeral: true
            });

        } catch (error) {
            console.error('Error fetching settings:', error);
            await interaction.reply({
                content: `❌ An error occurred while fetching settings:\n\`\`\`${error.message}\`\`\``,
                ephemeral: true
            });
        }
    }
};

function formatUptime(ms) {
    const seconds = Math.floor((ms / 1000) % 60);
    const minutes = Math.floor((ms / (1000 * 60)) % 60);
    const hours = Math.floor((ms / (1000 * 60 * 60)) % 24);
    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    
    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (seconds > 0) parts.push(`${seconds}s`);
    
    return parts.join(' ') || '0s';
}
