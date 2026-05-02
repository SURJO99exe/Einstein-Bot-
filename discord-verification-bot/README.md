# Discord Verification Bot

A complete, secure, and scalable Discord verification system built with **Node.js** and **discord.js v14**. Features button-based verification, captcha challenges, auto-kick, and comprehensive logging.

## ✨ Features

### Core Features
- ✅ **Button Verification** - Simple one-click verification with customizable embed
- 🧩 **Captcha System** - Math and text-based challenges to prevent bots
- 🎭 **Role Management** - Auto-assign verified/unverified roles
- 🔒 **Security** - Cooldown system, spam prevention, and attempt limiting
- 📋 **Logging** - Complete verification event logging
- ⏰ **Auto-Kick** - Automatically kick users who don't verify in time

### Security Features
- 🚫 **Spam Prevention** - Cooldown between verification attempts
- 🤖 **Bot Protection** - Automatically ignores bot accounts
- 🔐 **Attempt Limiting** - Block users after max failed attempts
- ⏳ **Time Limits** - Auto-kick unverified users after configured time
- 🛡️ **Verified Check** - Prevents already-verified users from clicking

### Admin Features
- ⚙️ **Setup Command** - `/setupverify` to easily configure verification
- 📊 **Settings Command** - `/settings` to view current configuration
- 🔧 **Customizable** - Configure roles, channels, and messages via .env
- 📝 **Detailed Logs** - Track all verification events

## 📋 Requirements

- **Node.js** 18.0.0 or higher
- **npm** or **yarn**
- A **Discord Bot Token**
- **Discord Server** with admin permissions

## 🚀 Setup Instructions

### Step 1: Install Node.js

Download and install Node.js from [nodejs.org](https://nodejs.org/) (LTS version recommended).

Verify installation:
```bash
node --version
npm --version
```

### Step 2: Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name
3. Go to **"Bot"** tab on the left sidebar
4. Click **"Add Bot"** and confirm
5. Under **"Privileged Gateway Intents"**, enable:
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **MESSAGE CONTENT INTENT**
6. Click **"Reset Token"** and copy your bot token (keep it secret!)

### Step 3: Invite Bot to Server

1. Go to **"OAuth2"** → **"URL Generator"**
2. Select scopes:
   - ✅ **bot**
   - ✅ **applications.commands**
3. Select bot permissions:
   - ✅ **Manage Roles**
   - ✅ **Kick Members**
   - ✅ **Send Messages**
   - ✅ **Embed Links**
   - ✅ **Read Message History**
   - ✅ **View Channels**
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### Step 4: Get Required IDs

#### Enable Developer Mode
1. Open Discord Settings
2. Go to **"Advanced"**
3. Enable **"Developer Mode"**

#### Get IDs
- **Guild ID**: Right-click your server name → **"Copy Server ID"**
- **Role IDs**: Right-click a role in server settings → **"Copy Role ID"**
- **Channel IDs**: Right-click a channel → **"Copy Channel ID"**

### Step 5: Install the Bot

1. **Extract/Navigate** to the bot folder:
```bash
cd discord-verification-bot
```

2. **Install dependencies**:
```bash
npm install
```

3. **Configure environment**:
```bash
copy .env.example .env
```

4. **Edit `.env` file** with your IDs and preferences:
```env
DISCORD_TOKEN=your_bot_token_here
CLIENT_ID=your_client_id_here
GUILD_ID=your_guild_id_here
VERIFIED_ROLE_ID=your_verified_role_id_here
VERIFY_CHANNEL_ID=your_verify_channel_id_here
LOG_CHANNEL_ID=your_log_channel_id_here
ENABLE_CAPTCHA=true
AUTO_KICK_MINUTES=30
```

### Step 6: Deploy Commands

Register slash commands with Discord:
```bash
npm run deploy
```

### Step 7: Start the Bot

```bash
npm start
```

Or for development with auto-reload:
```bash
npm run dev
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | ✅ Yes | Bot token from Discord Developer Portal |
| `CLIENT_ID` | ✅ Yes | Application ID from Discord Developer Portal |
| `GUILD_ID` | ✅ Yes | Your Discord server ID |
| `VERIFIED_ROLE_ID` | ✅ Yes | Role ID to assign when verified |
| `VERIFY_CHANNEL_ID` | ✅ Yes | Channel where verification message appears |
| `UNVERIFIED_ROLE_ID` | ❌ No | Role for unverified users (optional) |
| `LOG_CHANNEL_ID` | ❌ No | Channel for verification logs (optional) |
| `AUTO_KICK_MINUTES` | ❌ No | Minutes before auto-kick (0 = disabled) |
| `ENABLE_CAPTCHA` | ❌ No | Enable captcha (true/false) |
| `VERIFICATION_COOLDOWN` | ❌ No | Seconds between attempts (default: 10) |
| `ADMIN_ROLE_IDS` | ❌ No | Comma-separated admin role IDs |

### Customize Messages

Edit `config.js` to customize verification messages, colors, and other settings.

## 📚 Usage

### Setting Up Verification

1. **Run setup command**:
   ```
   /setupverify [channel] [verified_role]
   ```

2. The bot will send a verification message in the specified channel with a button

3. New users can click the button to verify

### Admin Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/setupverify` | Setup verification in a channel | Administrator |
| `/settings` | View bot configuration | Administrator |

### User Flow

1. **User joins server** → Receives DM notification
2. **User clicks verify button** in #verify channel
3. **If captcha enabled** → Solves math/text challenge
4. **Verified** → Gets verified role and confirmation message
5. **Log entry** → Event logged in log channel

## 🔒 Security Features Explained

### Cooldown System
- Users must wait 10 seconds between verification attempts
- Prevents spam clicking
- Configurable in `.env`

### Attempt Limiting
- Maximum 3 failed captcha attempts
- 5-minute block after max attempts
- Prevents brute force

### Auto-Kick
- Automatically removes users who don't verify within time limit
- Sends DM warning before kick
- Configurable time or disabled

### Bot Protection
- Automatically ignores bot accounts
- No verification messages for bots

## 🛠️ Troubleshooting

### Bot won't start
- Check `.env` file has all required variables
- Verify `DISCORD_TOKEN` is correct
- Ensure Node.js version is 18+

### Commands don't appear
- Run `npm run deploy` to register commands
- Wait up to 1 hour for global commands
- Check if bot has `applications.commands` scope

### Can't verify
- Check bot has **Manage Roles** permission
- Verify bot's role is **above** verified role in server settings
- Check bot can send messages in verify channel

### Captcha not working
- Ensure `ENABLE_CAPTCHA=true` in `.env`
- Check console for errors
- Verify math/text modules are loaded

### Auto-kick not working
- Set `AUTO_KICK_MINUTES` to value > 0
- Check bot has **Kick Members** permission
- Verify bot role is above roles it's managing

## 📁 File Structure

```
discord-verification-bot/
├── commands/
│   └── admin/
│       ├── setupverify.js    # Setup command
│       └── settings.js        # Settings command
├── handlers/
│   ├── ready.js              # Bot ready event
│   ├── guildMemberAdd.js    # New member handler
│   └── interactionCreate.js # Button/modal handler
├── utils/
│   └── captcha.js            # Captcha generation
├── config.js                 # Configuration
├── deploy-commands.js        # Command deployer
├── index.js                  # Main bot file
├── .env.example              # Example env file
├── package.json              # Dependencies
└── README.md                 # This file
```

## 🔄 Updating the Bot

1. Pull/download latest version
2. Run `npm install` to update dependencies
3. Run `npm run deploy` to update commands
4. Restart the bot

## 📝 Customization

### Changing Captcha Difficulty

Edit `utils/captcha.js`:
- Adjust number ranges in `generateMathCaptcha()`
- Add/remove challenges in `generateTextCaptcha()`
- Change `maxAttempts` in `config.js`

### Custom Embed Colors

Edit `config.js`:
```javascript
colors: {
    success: 0x00FF00,  // Green
    error: 0xFF0000,    // Red
    warning: 0xFFA500,  // Orange
    info: 0x0099FF,     // Blue
    neutral: 0x808080   // Gray
}
```

### Custom Verification Messages

Edit `config.js` messages section:
```javascript
messages: {
    verifyTitle: 'Your Custom Title',
    verifyDescription: 'Your custom description',
    // ... other messages
}
```

## 🤝 Support

For issues or questions:
1. Check Troubleshooting section above
2. Review console error messages
3. Verify all IDs and permissions

## 📄 License

This project is licensed under the MIT License.

## 🙏 Credits

Built with:
- [discord.js](https://discord.js.org/) - Discord API library
- [Node.js](https://nodejs.org/) - JavaScript runtime
- [dotenv](https://www.npmjs.com/package/dotenv) - Environment variables

---

**Made with ❤️ for secure Discord communities**
