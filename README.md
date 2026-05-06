# 🤖 Einstein Bot System (v2.5.0)

Einstein Bot is a powerful, multi-platform (Telegram & Discord) AI assistant built for the SURJO LIVE community. It features a persistent alarm system, advanced utility tools, and full mobile compatibility via Termux.

## 🚀 Key Features

- **Multi-Platform Sync**: Runs on both Discord and Telegram simultaneously.
- **AI Brain**: Integrated with Ollama/Groq for smart conversations and personality modes.
- **⏰ Persistent Alarms & Reminders**: Tasks are saved to JSON and survive bot restarts.
- **📱 Termux Mobile Ready**: Dedicated setup script for running on Android devices.
- **🛠️ Technical Suite**: Base64 tools, URL shortener, Morse code, and network diagnostics.
- **🛡️ Advanced Moderation**: Warning system, levels, and auto-mod for Discord.
- **🌐 Web Dashboard**: Real-time control panel and logs accessible via browser.

## 🛠️ Setup Instructions

### 💻 PC (Windows/Linux)
1. Clone the repository:
   ```bash
   git clone https://github.com/SURJO99exe/Einstein-Bot-.git
   cd Einstein-Bot-
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure `.env` file (see `.env.example`).
4. Run the bot:
   ```bash
   python bot.py
   ```

### 📱 Mobile (Termux)
1. Open Termux and install git: `pkg install git -y`
2. Clone the repo and enter the folder.
3. Run the setup script:
   ```bash
   bash setup_termux.sh
   ```
4. Run the bot: `python bot.py`

## 📜 Commands Preview

| Command | Platform | Description |
|---------|----------|-------------|
| `!alarm` | Both | Set a persistent alarm (HH:MM) |
| `!remind`| Both | Set a countdown reminder (10m, 1h) |
| `!net`   | Discord | Network tools (ping, diagnostics) |
| `!shorten`| Both | Shorten URLs via TinyURL |
| `!ai`    | Both | Chat with the AI Brain |
| `!status`| Both | View system resource usage |

## ⚙️ Environment Variables
Create a `.env` file with the following:
- `TELEGRAM_BOT_TOKEN`
- `DISCORD_BOT_TOKEN`
- `ALLOWED_USER_ID` (Admin ID)
- `OPENWEATHER_API_KEY` (Optional)
- `NEWS_API_KEY` (Optional)

## 📄 License
This project is licensed under the MIT License.

Created with ❤️ by **SURJO99exe**
