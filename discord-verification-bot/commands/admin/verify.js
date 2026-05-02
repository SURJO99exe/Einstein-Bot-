/**
 * Manual Verify Command
 * Admin command to manually verify a user
 */

const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { EmbedBuilder } = require('discord.js');
const { config } = require('../../config');
const { logEvent } = require('../../handlers/ready');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('verify')
        .setDescription('Manually verify a user (Admin only)')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
        .addUserOption(option =>
            option
                .setName('user')
                .setDescription('The user to verify')
                .setRequired(true)
        )
        .addStringOption(option =>
            option
                .setName('reason')
                .setDescription('Reason for manual verification')
                .setRequired(false)
        ),

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
            const targetUser = interaction.options.getUser('user');
            const reason = interaction.options.getString('reason') || 'Manual verification by admin';
            
            // Get member from guild
            const member = await interaction.guild.members.fetch(targetUser.id).catch(() => null);
            
            if (!member) {
                return await interaction.editReply({
                    content: `❌ User ${targetUser.tag} is not in this server.`,
                });
            }

            // Check if already verified
            if (member.roles.cache.has(config.verifiedRoleId)) {
                return await interaction.editReply({
                    content: `⚠️ ${targetUser.tag} is already verified.`,
                });
            }

            // Get verified role
            const verifiedRole = await interaction.guild.roles.fetch(config.verifiedRoleId);
            if (!verifiedRole) {
                return await interaction.editReply({
                    content: '❌ Verified role not found. Please check your configuration.',
                });
            }

            // Add verified role
            await member.roles.add(verifiedRole);

            // Remove unverified role if configured
            if (config.unverifiedRoleId) {
                const unverifiedRole = await interaction.guild.roles.fetch(config.unverifiedRoleId).catch(() => null);
                if (unverifiedRole && member.roles.cache.has(config.unverifiedRoleId)) {
                    await member.roles.remove(unverifiedRole);
                }
            }

            // Remove from pending verifications
            const guildPending = client.pendingVerifications.get(interaction.guild.id);
            if (guildPending) {
                guildPending.delete(targetUser.id);
            }

            // Clear any cooldowns or blocks
            client.cooldowns.delete(`${targetUser.id}-verify`);
            client.verificationAttempts.delete(targetUser.id);

            // Send confirmation
            const successEmbed = new EmbedBuilder()
                .setTitle('✅ Manual Verification Complete')
                .setDescription(`${targetUser.tag} has been manually verified.`)
                .setColor(config.colors.success)
                .addFields(
                    { name: 'User', value: `${targetUser.tag} (${targetUser.id})`, inline: true },
                    { name: 'Verified By', value: `${interaction.user.tag}`, inline: true },
                    { name: 'Reason', value: reason, inline: false }
                )
                .setTimestamp();

            await interaction.editReply({
                embeds: [successEmbed]
            });

            // Send DM to verified user
            try {
                const dmEmbed = new EmbedBuilder()
                    .setTitle('✅ You Have Been Verified!')
                    .setDescription(`You have been manually verified in **${interaction.guild.name}** by an administrator.`)
                    .setColor(config.colors.success)
                    .setTimestamp();

                await targetUser.send({ embeds: [dmEmbed] });
            } catch (error) {
                // User has DMs disabled, that's okay
                console.log(`Could not send DM to ${targetUser.tag}`);
            }

            // Log the manual verification
            logEvent(client, interaction.guild, 'Manual Verification', targetUser, 
                `Verified by ${interaction.user.tag}: ${reason}`);

            console.log(`✅ Manual verification: ${targetUser.tag} by ${interaction.user.tag}`);

        } catch (error) {
            console.error('Error in manual verification:', error);
            await interaction.editReply({
                content: `❌ An error occurred while verifying the user:\n\`\`\`${error.message}\`\`\``
            });
        }
    }
};
