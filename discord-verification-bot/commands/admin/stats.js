/**
 * Stats Command
 * View verification statistics
 */

const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { EmbedBuilder } = require('discord.js');
const { config } = require('../../config');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('stats')
        .setDescription('View verification statistics')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

    async execute(interaction, client) {
        // Check if user has admin permissions
        if (!interaction.memberPermissions.has(PermissionFlagsBits.Administrator)) {
            return await interaction.reply({
                content: '❌ You need Administrator permission to use this command.',
                ephemeral: true
            });
        }

        await interaction.deferReply({ ephemeral: true });

        try {
            const guild = interaction.guild;
            
            // Get statistics from client data
            const pendingVerifications = client.pendingVerifications.get(guild.id) || new Map();
            const activeCooldowns = Array.from(client.cooldowns.entries()).filter(([key]) => key.endsWith('-verify'));
            const blockedUsers = Array.from(client.verificationAttempts.entries()).filter(([_, data]) => data.blocked);
            
            // Get verified count
            const verifiedRole = await guild.roles.fetch(config.verifiedRoleId).catch(() => null);
            const verifiedCount = verifiedRole ? verifiedRole.members.size : 0;
            
            // Get unverified count
            let unverifiedCount = 0;
            if (config.unverifiedRoleId) {
                const unverifiedRole = await guild.roles.fetch(config.unverifiedRoleId).catch(() => null);
                if (unverifiedRole) {
                    unverifiedCount = unverifiedRole.members.size;
                }
            } else {
                // Calculate unverified as total - verified (bots not counted)
                const botCount = guild.members.cache.filter(m => m.user.bot).size;
                unverifiedCount = guild.memberCount - verifiedCount - botCount;
            }
            
            // Calculate verification rate
            const totalMembers = guild.memberCount - guild.members.cache.filter(m => m.user.bot).size;
            const verificationRate = totalMembers > 0 ? ((verifiedCount / totalMembers) * 100).toFixed(1) : 0;
            
            // Create stats embed
            const statsEmbed = new EmbedBuilder()
                .setTitle('📊 Verification Statistics')
                .setDescription(`Verification statistics for ${guild.name}`)
                .setColor(config.colors.info)
                .setThumbnail(guild.iconURL({ dynamic: true }))
                .addFields(
                    { 
                        name: '👥 User Statistics', 
                        value: [
                            `**Total Members:** ${guild.memberCount}`,
                            `**Verified Users:** ${verifiedCount}`,
                            `**Pending Verification:** ${pendingVerifications.size}`,
                            `**Unverified Users:** ${unverifiedCount}`,
                            `**Verification Rate:** ${verificationRate}%`
                        ].join('\n'),
                        inline: false 
                    },
                    { 
                        name: '🔒 Security Statistics', 
                        value: [
                            `**Active Cooldowns:** ${activeCooldowns.length}`,
                            `**Blocked Users:** ${blockedUsers.length}`,
                            `**Max Attempts:** ${config.security.maxAttempts}`,
                            `**Cooldown Duration:** ${config.verificationCooldown}s`
                        ].join('\n'),
                        inline: true 
                    },
                    { 
                        name: '⚙️ Configuration', 
                        value: [
                            `**Captcha:** ${config.enableCaptcha ? '✅ Enabled' : '❌ Disabled'}`,
                            `**Auto-Kick:** ${config.autoKickMinutes > 0 ? `✅ ${config.autoKickMinutes}min` : '❌ Disabled'}`,
                            `**Log Channel:** ${config.logChannelId ? '✅ Set' : '❌ Not Set'}`
                        ].join('\n'),
                        inline: true 
                    }
                )
                .setFooter({ text: `Requested by ${interaction.user.tag}` })
                .setTimestamp();

            // Add blocked users list if any
            if (blockedUsers.length > 0) {
                const blockedList = blockedUsers
                    .slice(0, 5) // Show max 5 blocked users
                    .map(([userId, data]) => {
                        const timeLeft = Math.ceil((data.blockExpiry - Date.now()) / 60000);
                        return `• <@${userId}> (${timeLeft}m left)`;
                    })
                    .join('\n');
                
                statsEmbed.addFields({
                    name: '🚫 Currently Blocked Users',
                    value: blockedUsers.length > 5 
                        ? `${blockedList}\n... and ${blockedUsers.length - 5} more`
                        : blockedList || 'None',
                    inline: false
                });
            }

            // Add pending verifications list if any
            if (pendingVerifications.size > 0) {
                const pendingList = Array.from(pendingVerifications.entries())
                    .slice(0, 5)
                    .map(([userId, data]) => {
                        const timeAgo = Math.ceil((Date.now() - data.joinTime) / 60000);
                        return `• <@${userId}> (${timeAgo}m ago)`;
                    })
                    .join('\n');
                
                statsEmbed.addFields({
                    name: '⏳ Pending Verifications',
                    value: pendingVerifications.size > 5
                        ? `${pendingList}\n... and ${pendingVerifications.size - 5} more`
                        : pendingList || 'None',
                    inline: false
                });
            }

            await interaction.editReply({
                embeds: [statsEmbed]
            });

        } catch (error) {
            console.error('Error fetching stats:', error);
            await interaction.editReply({
                content: `❌ An error occurred while fetching statistics:\n\`\`\`${error.message}\`\`\``
            });
        }
    }
};
