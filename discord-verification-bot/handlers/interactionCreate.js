/**
 * Interaction Create Event Handler
 * Handles button clicks and modal submissions
 */

const { 
    EmbedBuilder, 
    ActionRowBuilder, 
    ButtonBuilder, 
    ButtonStyle,
    ModalBuilder,
    TextInputBuilder,
    TextInputStyle,
    InteractionType
} = require('discord.js');
const { config } = require('../config');
const { logEvent } = require('./ready');
const { generateCaptcha, verifyCaptcha } = require('../utils/captcha');

module.exports = {
    name: 'interactionCreate',
    once: false,
    async execute(interaction, client) {
        // Handle slash commands
        if (interaction.isChatInputCommand()) {
            const command = client.commands.get(interaction.commandName);
            
            if (!command) {
                console.error(`No command matching ${interaction.commandName} was found.`);
                return;
            }
            
            try {
                await command.execute(interaction, client);
            } catch (error) {
                console.error(error);
                const errorMessage = {
                    content: 'There was an error while executing this command!',
                    ephemeral: true
                };
                
                if (interaction.replied || interaction.deferred) {
                    await interaction.followUp(errorMessage);
                } else {
                    await interaction.reply(errorMessage);
                }
            }
            return;
        }
        
        // Handle button clicks
        if (interaction.isButton()) {
            await handleButtonClick(interaction, client);
            return;
        }
        
        // Handle modal submissions
        if (interaction.type === InteractionType.ModalSubmit) {
            await handleModalSubmit(interaction, client);
            return;
        }
    }
};

async function handleButtonClick(interaction, client) {
    const { customId, user, member } = interaction;
    
    // Handle verify button
    if (customId === 'verify_button') {
        // Check if user is already verified
        if (member.roles.cache.has(config.verifiedRoleId)) {
            return await interaction.reply({
                content: config.messages.alreadyVerified,
                ephemeral: true
            });
        }
        
        // Check cooldown
        const cooldownKey = `${user.id}-verify`;
        const now = Date.now();
        const cooldownAmount = config.verificationCooldown * 1000;
        
        if (client.cooldowns.has(cooldownKey)) {
            const expirationTime = client.cooldowns.get(cooldownKey) + cooldownAmount;
            
            if (now < expirationTime) {
                const timeLeft = Math.ceil((expirationTime - now) / 1000);
                return await interaction.reply({
                    content: config.messages.cooldownMessage.replace('{seconds}', timeLeft),
                    ephemeral: true
                });
            }
        }
        
        // Set cooldown
        client.cooldowns.set(cooldownKey, now);
        setTimeout(() => client.cooldowns.delete(cooldownKey), cooldownAmount);
        
        // Check verification attempts
        const attempts = client.verificationAttempts.get(user.id) || { count: 0, blocked: false, blockExpiry: 0 };
        
        if (attempts.blocked && now < attempts.blockExpiry) {
            const minutesLeft = Math.ceil((attempts.blockExpiry - now) / 60000);
            return await interaction.reply({
                content: `🚫 You are temporarily blocked from verifying. Try again in ${minutesLeft} minutes.`,
                ephemeral: true
            });
        } else if (attempts.blocked) {
            // Unblock user
            attempts.blocked = false;
            attempts.count = 0;
        }
        
        // If captcha is enabled, show captcha modal
        if (config.enableCaptcha) {
            const captcha = generateCaptcha();
            
            // Store captcha answer for this user
            const pendingData = client.pendingVerifications.get(interaction.guild.id)?.get(user.id);
            if (pendingData) {
                pendingData.captchaAnswer = captcha.answer;
                pendingData.captchaQuestion = captcha.question;
            }
            
            // Create modal for captcha
            const modal = new ModalBuilder()
                .setCustomId('captcha_modal')
                .setTitle('🧩 Verification Captcha');
            
            const captchaInput = new TextInputBuilder()
                .setCustomId('captcha_answer')
                .setLabel(`Solve: ${captcha.question}`)
                .setPlaceholder('Enter your answer here...')
                .setStyle(TextInputStyle.Short)
                .setMinLength(1)
                .setMaxLength(10)
                .setRequired(true);
            
            const row = new ActionRowBuilder().addComponents(captchaInput);
            modal.addComponents(row);
            
            await interaction.showModal(modal);
        } else {
            // No captcha, verify directly
            await verifyUser(interaction, client, member, user);
        }
    }
}

async function handleModalSubmit(interaction, client) {
    const { customId, user, member, guild } = interaction;
    
    if (customId === 'captcha_modal') {
        const answer = interaction.fields.getTextInputValue('captcha_answer');
        const pendingData = client.pendingVerifications.get(guild.id)?.get(user.id);
        
        if (!pendingData || !pendingData.captchaAnswer) {
            return await interaction.reply({
                content: '❌ Verification session expired. Please try again.',
                ephemeral: true
            });
        }
        
        // Verify captcha answer
        const isCorrect = verifyCaptcha(answer, pendingData.captchaAnswer);
        
        if (!isCorrect) {
            // Increment failed attempts
            let attempts = client.verificationAttempts.get(user.id) || { count: 0, blocked: false, blockExpiry: 0 };
            attempts.count++;
            attempts.lastAttempt = Date.now();
            
            if (attempts.count >= config.security.maxAttempts) {
                attempts.blocked = true;
                attempts.blockExpiry = Date.now() + config.security.blockDuration;
                client.verificationAttempts.set(user.id, attempts);
                
                logEvent(client, guild, 'Verification Blocked', user, `Too many failed captcha attempts (${attempts.count})`);
                
                return await interaction.reply({
                    content: `🚫 Too many failed attempts. You are blocked from verifying for 5 minutes.`,
                    ephemeral: true
                });
            }
            
            client.verificationAttempts.set(user.id, attempts);
            
            const remainingAttempts = config.security.maxAttempts - attempts.count;
            
            return await interaction.reply({
                content: `❌ Incorrect answer. You have ${remainingAttempts} attempt(s) remaining.`,
                ephemeral: true
            });
        }
        
        // Captcha passed, verify user
        await verifyUser(interaction, client, member, user, true);
    }
}

async function verifyUser(interaction, client, member, user, passedCaptcha = false) {
    try {
        // Add verified role
        const verifiedRole = await interaction.guild.roles.fetch(config.verifiedRoleId);
        if (!verifiedRole) {
            throw new Error('Verified role not found');
        }
        
        await member.roles.add(verifiedRole);
        
        // Remove unverified role if configured
        if (config.unverifiedRoleId) {
            const unverifiedRole = await interaction.guild.roles.fetch(config.unverifiedRoleId).catch(() => null);
            if (unverifiedRole && member.roles.cache.has(config.unverifiedRoleId)) {
                await member.roles.remove(config.unverifiedRoleId);
            }
        }
        
        // Remove from pending verifications
        const guildPending = client.pendingVerifications.get(interaction.guild.id);
        if (guildPending) {
            guildPending.delete(user.id);
        }
        
        // Clear verification attempts
        client.verificationAttempts.delete(user.id);
        
        // Send success message
        const successEmbed = new EmbedBuilder()
            .setTitle('✅ Verification Successful!')
            .setDescription(config.messages.verifiedSuccess)
            .setColor(config.colors.success)
            .setTimestamp();
        
        await interaction.reply({
            embeds: [successEmbed],
            ephemeral: true
        });
        
        // Log the verification
        const details = passedCaptcha ? 'Verified with captcha' : 'Verified (no captcha)';
        logEvent(client, interaction.guild, 'User Verified', user, details);
        
        console.log(`✅ User verified: ${user.tag} (${user.id})`);
        
    } catch (error) {
        console.error('Error verifying user:', error);
        
        await interaction.reply({
            content: config.messages.verificationFailed,
            ephemeral: true
        });
        
        logEvent(client, interaction.guild, 'Verification Failed', user, error.message);
    }
}
