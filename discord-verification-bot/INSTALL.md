# Installation Guide

## Quick Start (5 minutes)

### 1. Install Dependencies
```bash
cd discord-verification-bot
npm install
```

### 2. Configure Environment
```bash
copy .env.example .env
```
Edit `.env` and fill in your Discord bot token and IDs.

### 3. Deploy Commands
```bash
npm run deploy
```

### 4. Start Bot
```bash
npm start
```

## Step-by-Step Setup

### Prerequisites
- Node.js 18+ installed
- Discord account with a server
- Bot token from Discord Developer Portal

### Detailed Steps

1. **Install Node.js**
   - Download from https://nodejs.org/
   - Choose LTS version
   - Verify: `node --version`

2. **Create Discord Bot**
   - Go to https://discord.com/developers/applications
   - New Application → Bot → Add Bot
   - Enable SERVER MEMBERS INTENT
   - Copy token

3. **Get Your IDs**
   - Enable Developer Mode in Discord (Settings → Advanced)
   - Right-click server name → Copy Server ID = GUILD_ID
   - Right-click role → Copy Role ID = VERIFIED_ROLE_ID
   - Right-click channel → Copy Channel ID = VERIFY_CHANNEL_ID

4. **Configure Bot**
   ```env
   DISCORD_TOKEN=your_token_here
   CLIENT_ID=your_app_id_here
   GUILD_ID=your_server_id_here
   VERIFIED_ROLE_ID=your_verified_role_id_here
   VERIFY_CHANNEL_ID=your_verify_channel_id_here
   ```

5. **Run Setup**
   ```bash
   npm install
   npm run deploy
   npm start
   ```

6. **Setup Verification**
   - In Discord: `/setupverify`
   - Select channel where verify button should appear
   - Done!

## Troubleshooting

### "DISCORD_TOKEN not set"
- Check `.env` file exists
- Ensure token is correct
- No quotes around token

### "Cannot find module"
- Run `npm install` again
- Delete `node_modules` and reinstall

### Commands not showing
- Run `npm run deploy`
- Wait 1 hour for global commands
- Check bot has `applications.commands` scope

### Bot can't assign roles
- Bot role must be ABOVE verified role
- Bot needs "Manage Roles" permission
- Role hierarchy is important

## Updating

```bash
git pull  # or download new version
npm install
npm run deploy
npm start
```

## Support

Check README.md for detailed documentation.
