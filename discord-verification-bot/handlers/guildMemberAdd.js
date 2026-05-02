/**
 * Guild Member Add Event Handler
 * Triggered when a new user joins the server
 * Auto-activates verification system on first join
 */

const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const { config } = require('../config');
const { logEvent } = require('./ready');

// Track if verification message has been auto-setup
let verificationMessageSent = false;

module.exports = {
    name: 'guildMemberAdd',
    once: false,
    async execute(member, client) {
        // Ignore bots
        if (member.user.bot) {
            console.log(`🤖 Ignored bot join: ${member.user.tag}`);
            return;
        }
        
        // Check if correct guild
        if (member.guild.id !== config.guildId) return;
        
        console.log(`👤 New member joined: ${member.user.tag} (${member.user.id})`);
        
        // AUTO-SETUP: Send verification message if not already done
        if (!verificationMessageSent && config.verifyChannelId) {
            await autoSetupVerification(client, member.guild);
            verificationMessageSent = true;
        }
        
        // Add to pending verifications
        if (!client.pendingVerifications.has(member.guild.id)) {
            client.pendingVerifications.set(member.guild.id, new Map());
        }
        
        const guildPending = client.pendingVerifications.get(member.guild.id);
        guildPending.set(member.id, {
            joinTime: Date.now(),
            userId: member.id,
            attempts: 0,
            captchaAnswer: null,
            autoOn: true  // Mark as auto-on system
        });
        
        // Assign unverified role if configured
        if (config.unverifiedRoleId) {
            try {
                const unverifiedRole = await member.guild.roles.fetch(config.unverifiedRoleId);
                if (unverifiedRole) {
                    await member.roles.add(unverifiedRole);
                    console.log(`   🎭 Assigned unverified role to ${member.user.tag}`);
                }
            } catch (error) {
                console.error('Error assigning unverified role:', error.message);
            }
        }
        
        // Send DM to user with verification link
        try {
            const dmEmbed = new EmbedBuilder()
                .setTitle(`Welcome to ${member.guild.name}! 🎉`)
                .setDescription(`Please verify yourself to gain access to all channels.`)
                .setColor(config.colors.info)
                .addFields({
                    name: '📝 How to Verify',
                    value: `Go to <#${config.verifyChannelId}> and click the **✅ Verify** button!`,
                    inline: false
                })
                .setTimestamp();
            
            if (config.autoKickMinutes > 0) {
                dmEmbed.addFields({
                    name: '⏰ Time Limit',
                    value: `You have **${config.autoKickMinutes} minutes** to verify or you will be automatically removed.`
                });
            }
            
            await member.send({ embeds: [dmEmbed] });
            console.log(`   📨 Sent welcome DM to ${member.user.tag}`);
        } catch (error) {
            // User has DMs disabled, that's okay
            console.log(`   📭 Could not send DM to ${member.user.tag} (DMs disabled)`);
        }
        
        // Send ephemeral notification in verify channel mentioning the new user
        try {
            const verifyChannel = await member.guild.channels.fetch(config.verifyChannelId).catch(() => null);
            if (verifyChannel) {
                // Create welcome message that auto-deletes after 10 seconds
                const welcomeMsg = await verifyChannel.send({
                    content: `👋 Welcome ${member}! Please click the button above to verify yourself.`,
                    allowedMentions: { users: [member.id] }
                });
                
                // Delete after 10 seconds
                setTimeout(() => {
                    welcomeMsg.delete().catch(() => {});
                }, 10000);
            }
        } catch (error) {
            console.log(`   ⚠️ Could not send welcome message in verify channel`);
        }
        
        // Log the join
        logEvent(client, member.guild, 'Member Joined (Auto-On)', member.user, 'Verification system auto-activated');
        
        console.log(`   ✅ Auto-on verification active for ${member.user.tag}`);
    }
};

/**
 * Auto-setup verification message in channel
 */
async function autoSetupVerification(client, guild) {
    try {
        const verifyChannel = await guild.channels.fetch(config.verifyChannelId).catch(() => null);
        if (!verifyChannel) {
            console.log('⚠️ Verify channel not found for auto-setup');
            return;
        }
        
        // Check if verification message already exists
        const messages = await verifyChannel.messages.fetch({ limit: 10 }).catch(() => new Map());
        const hasVerifyMessage = Array.from(messages.values()).some(msg => 
            msg.author.id === client.user.id && 
            msg.components.length > 0 &&
            msg.embeds.length > 0
        );
        
        if (hasVerifyMessage) {
            console.log('✅ Verification message already exists, skipping auto-setup');
            return;
        }
        
        // Get verified role
        const verifiedRole = await guild.roles.fetch(config.verifiedRoleId).catch(() => null);
        
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
                    value: `• Access to all channels\n• ${verifiedRole || 'Verified'} role\n• Full server permissions`,
                    inline: true 
                }
            )
            .setFooter({ text: config.messages.verifyFooter })
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
        await verifyChannel.send({
            embeds: [verifyEmbed],
            components: [row]
        });
        
        console.log(`🚀 Auto-setup: Verification message sent in #${verifyChannel.name}`);
        
        // Log the auto-setup
        logEvent(client, guild, 'Auto-Setup Complete', client.user, 
            `Verification system auto-activated in #${verifyChannel.name}`);
        
    } catch (error) {
        console.error('❌ Auto-setup error:', error.message);
    }
}
