/**
 * Unverify Command
 * Admin command to remove verification from a user
 */

const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { EmbedBuilder } = require('discord.js');
const { config } = require('../../config');
const { logEvent } = require('../../handlers/ready');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('unverify')
        .setDescription('Remove verification from a user (Admin only)')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
        .addUserOption(option =>
            option
                .setName('user')
                .setDescription('The user to unverify')
                .setRequired(true)
        )
        .addStringOption(option =>
            option
                .setName('reason')
                .setDescription('Reason for removing verification')
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
            const reason = interaction.options.getString('reason') || 'No reason provided';
            
            // Get member from guild
            const member = await interaction.guild.members.fetch(targetUser.id).catch(() => null);
            
            if (!member) {
                return await interaction.editReply({
                    content: `❌ User ${targetUser.tag} is not in this server.`,
                });
            }

            // Check if user is verified
            if (!member.roles.cache.has(config.verifiedRoleId)) {
                return await interaction.editReply({
                    content: `⚠️ ${targetUser.tag} is not verified.`,
                });
            }

            // Get verified role
            const verifiedRole = await interaction.guild.roles.fetch(config.verifiedRoleId);
            if (!verifiedRole) {
                return await interaction.editReply({
                    content: '❌ Verified role not found. Please check your configuration.',
                });
            }

            // Remove verified role
            await member.roles.remove(verifiedRole);

            // Add unverified role if configured
            if (config.unverifiedRoleId) {
                const unverifiedRole = await interaction.guild.roles.fetch(config.unverifiedRoleId).catch(() => null);
                if (unverifiedRole) {
                    await member.roles.add(unverifiedRole);
                }
            }

            // Add back to pending verifications
            if (!client.pendingVerifications.has(interaction.guild.id)) {
                client.pendingVerifications.set(interaction.guild.id, new Map());
            }
            const guildPending = client.pendingVerifications.get(interaction.guild.id);
            guildPending.set(targetUser.id, {
                joinTime: Date.now(),
                userId: targetUser.id,
                attempts: 0,
                captchaAnswer: null,
                unverified: true
            });

            // Send confirmation
            const successEmbed = new EmbedBuilder()
                .setTitle('🚫 Verification Removed')
                .setDescription(`${targetUser.tag} has been unverified.`)
                .setColor(config.colors.warning)
                .addFields(
                    { name: 'User', value: `${targetUser.tag} (${targetUser.id})`, inline: true },
                    { name: 'Removed By', value: `${interaction.user.tag}`, inline: true },
                    { name: 'Reason', value: reason, inline: false }
                )
                .setTimestamp();

            await interaction.editReply({
                embeds: [successEmbed]
            });

            // Send DM to unverified user
            try {
                const dmEmbed = new EmbedBuilder()
                    .setTitle('🚫 Your Verification Has Been Removed')
                    .setDescription(`Your verification in **${interaction.guild.name}** has been removed by an administrator.`)
                    .setColor(config.colors.warning)
                    .addFields(
                        { name: 'Reason', value: reason }
                    )
                    .setFooter({ text: 'You will need to verify again to access the server.' })
                    .setTimestamp();

                await targetUser.send({ embeds: [dmEmbed] });
            } catch (error) {
                // User has DMs disabled, that's okay
                console.log(`Could not send DM to ${targetUser.tag}`);
            }

            // Log the unverification
            logEvent(client, interaction.guild, 'Verification Removed', targetUser, 
                `Removed by ${interaction.user.tag}: ${reason}`);

            console.log(`🚫 Verification removed: ${targetUser.tag} by ${interaction.user.tag}`);

        } catch (error) {
            console.error('Error in unverification:', error);
            await interaction.editReply({
                content: `❌ An error occurred while removing verification:\n\`\`\`${error.message}\`\`\``
            });
        }
    }
};
