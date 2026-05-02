/**
 * Configuration file for Discord Verification Bot
 * Loads environment variables and provides configuration object
 */

require('dotenv').config();

const config = {
    // Bot settings
    token: process.env.DISCORD_TOKEN,
    clientId: process.env.CLIENT_ID,
    guildId: process.env.GUILD_ID,
    
    // Role IDs
    verifiedRoleId: process.env.VERIFIED_ROLE_ID,
    unverifiedRoleId: process.env.UNVERIFIED_ROLE_ID || null,
    adminRoleIds: process.env.ADMIN_ROLE_IDS ? process.env.ADMIN_ROLE_IDS.split(',') : [],
    
    // Channel IDs
    verifyChannelId: process.env.VERIFY_CHANNEL_ID,
    logChannelId: process.env.LOG_CHANNEL_ID,
    
    // Verification settings
    autoKickMinutes: parseInt(process.env.AUTO_KICK_MINUTES) || 30,
    enableCaptcha: process.env.ENABLE_CAPTCHA === 'true',
    verificationCooldown: parseInt(process.env.VERIFICATION_COOLDOWN) || 10,
    
    // Colors for embeds
    colors: {
        success: 0x00FF00,      // Green
        error: 0xFF0000,        // Red
        warning: 0xFFA500,      // Orange
        info: 0x0099FF,         // Blue
        neutral: 0x808080       // Gray
    },
    
    // Messages
    messages: {
        verifyButtonLabel: '✅ Verify',
        verifyButtonEmoji: '✅',
        verifyTitle: 'Server Verification',
        verifyDescription: 'Welcome! Please click the button below to verify yourself and gain access to the server.',
        verifyFooter: 'Complete the verification to unlock all channels',
        
        verifiedSuccess: '✅ You have been successfully verified! Welcome to the server.',
        alreadyVerified: 'You are already verified!',
        verificationFailed: '❌ Verification failed. Please try again or contact a moderator.',
        cooldownMessage: '⏳ Please wait {seconds} seconds before trying again.',
        captchaPrompt: '🧩 Please solve this captcha: {question}',
        autoKickWarning: '⚠️ You will be kicked in {minutes} minutes if you don\'t verify.',
        kickedMessage: 'You were kicked from {server} for not verifying within the required time.'
    },
    
    // Security settings
    security: {
        maxAttempts: 3,                 // Max captcha attempts
        blockDuration: 300000,          // 5 minutes block after max attempts
        cleanupInterval: 60000,         // Cleanup old data every minute
        verificationExpiry: 3600000     // Verification data expires after 1 hour
    }
};

// Validate required configuration
function validateConfig() {
    const required = [
        'token',
        'clientId',
        'guildId',
        'verifiedRoleId',
        'verifyChannelId'
    ];
    
    const missing = required.filter(key => !config[key]);
    
    if (missing.length > 0) {
        console.error('❌ Missing required environment variables:');
        missing.forEach(key => console.error(`   - ${key}`));
        console.error('\nPlease check your .env file and set all required variables.');
        console.error('See .env.example for reference.');
        process.exit(1);
    }
    
    console.log('✅ Configuration validated successfully!');
    return true;
}

module.exports = { config, validateConfig };
