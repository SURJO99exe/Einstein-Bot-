/**
 * Setup Verify Command
 * Admin command to setup the verification system in a channel
 */

const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const { config } = require('../../config');
const { logEvent } = require('../../handlers/ready');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('setupverify')
        .setDescription('Setup the verification system in the current channel')
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
        .addChannelOption(option =>
            option
                .setName('channel')
                .setDescription('The channel to setup verification in (defaults to current channel)')
                .setRequired(false)
        )
        .addRoleOption(option =>
            option
                .setName('verified_role')
                .setDescription('The role to assign when verified (defaults to configured role)')
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
            // Get target channel
            const targetChannel = interaction.options.getChannel('channel') || interaction.channel;
            
            // Get verified role
            let verifiedRole = interaction.options.getRole('verified_role');
            if (!verifiedRole) {
                verifiedRole = await interaction.guild.roles.fetch(config.verifiedRoleId).catch(() => null);
            }

            if (!verifiedRole) {
                return await interaction.editReply({
                    content: '❌ Verified role not found. Please configure it in the .env file or provide it as an option.',
                });
            }

            // Check bot permissions in target channel
            const botMember = interaction.guild.members.me;
            const channelPermissions = targetChannel.permissionsFor(botMember);
            
            if (!channelPermissions.has(PermissionFlagsBits.SendMessages)) {
                return await interaction.editReply({
                    content: `❌ I don't have permission to send messages in ${targetChannel}.`,
                });
            }

            if (!channelPermissions.has(PermissionFlagsBits.EmbedLinks)) {
                return await interaction.editReply({
                    content: `❌ I don't have permission to embed links in ${targetChannel}.`,
                });
            }

            // Create verification embed
            const verifyEmbed = new EmbedBuilder()
                .setTitle(config.messages.verifyTitle)
                .setDescription(config.messages.verifyDescription)
                .setColor(config.colors.info)
                .addFields(
                    { 
                        name: '📝 Instructions', 
                        value: 'Click the button below to verify yourself and gain access to the server.',
                        inline: false 
                    },
                    { 
                        name: '✅ What You Get', 
                        value: `• Access to all channels\n• ${verifiedRole} role\n• Full server permissions`,
                        inline: true 
                    }
                )
                .setFooter({ 
                    text: config.messages.verifyFooter 
                })
                .setTimestamp();

            // Add captcha info if enabled
            if (config.enableCaptcha) {
                verifyEmbed.addFields({
                    name: '🧩 Security Check',
                    value: 'A simple verification challenge will appear after clicking the button.',
                    inline: false
                });
            }

            // Add auto-kick warning if enabled
            if (config.autoKickMinutes > 0) {
                verifyEmbed.addFields({
                    name: '⏰ Time Limit',
                    value: `Please verify within **${config.autoKickMinutes} minutes** or you will be automatically removed.`,
                    inline: false
                });
            }

            // Create verify button
            const row = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('verify_button')
                        .setLabel(config.messages.verifyButtonLabel)
                        .setStyle(ButtonStyle.Success)
                        .setEmoji(config.messages.verifyButtonEmoji)
                );

            // Send verification message
            const verifyMessage = await targetChannel.send({
                embeds: [verifyEmbed],
                components: [row]
            });

            // Create setup confirmation embed
            const confirmationEmbed = new EmbedBuilder()
                .setTitle('✅ Verification System Setup Complete!')
                .setDescription(`The verification system has been set up in ${targetChannel}.`)
                .setColor(config.colors.success)
                .addFields(
                    { name: '📍 Channel', value: `${targetChannel} (${targetChannel.id})`, inline: true },
                    { name: '🎭 Verified Role', value: `${verifiedRole}`, inline: true },
                    { name: '🧩 Captcha', value: config.enableCaptcha ? 'Enabled' : 'Disabled', inline: true },
                    { name: '⏰ Auto-Kick', value: config.autoKickMinutes > 0 ? `${config.autoKickMinutes} minutes` : 'Disabled', inline: true },
                    { name: '📨 Message ID', value: verifyMessage.id, inline: false }
                )
                .setFooter({ text: 'Users can now verify by clicking the button!' })
                .setTimestamp();

            await interaction.editReply({
                embeds: [confirmationEmbed]
            });

            // Log the setup
            logEvent(client, interaction.guild, 'Verification Setup', interaction.user, 
                `Setup in ${targetChannel.name} with role @${verifiedRole.name}`);

            console.log(`✅ Verification system setup by ${interaction.user.tag} in #${targetChannel.name}`);

        } catch (error) {
            console.error('Error setting up verification:', error);
            await interaction.editReply({
                content: `❌ An error occurred while setting up the verification system:\n\`\`\`${error.message}\`\`\``
            });
        }
    }
};
