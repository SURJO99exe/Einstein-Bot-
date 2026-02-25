# Einstein Bot 🤖

Einstein Bot is a multi-functional advanced bot capable of managing tasks across Telegram and Discord. It includes AI-driven features, system monitoring, social media management, and more.

## ✨ Features

- **AI Chat & Generation**: Integrated with OpenAI, Claude, and Ollama.
- **System Monitoring**: Track CPU, RAM, and Disk usage in real-time.
- **Social Media Control**: Manage Facebook, YouTube, TikTok, and Twitter.
- **Media Explorer**: Browse trending YouTube videos and search content.
- **Utilities**: Weather updates, web search (DuckDuckGo), and QR code generation.
- **Remote Control**: Execute CMD commands and take screenshots remotely.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/) (optional, for local AI)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/SURJO99exe/Einstein-Bot-.git
   cd Einstein-Bot-
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Create a `.env` file based on `.env.example`.
   - Add your bot tokens and API keys.

### Running the Bot

```bash
python bot.py
```

## 🛠️ Configuration

The bot uses a `.env` file for configuration. Key variables include:
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from @BotFather.
- `DISCORD_BOT_TOKEN`: Your Discord bot token.
- `ALLOWED_USER_ID`: Your Telegram user ID for restricted access.

## 📁 Project Structure

- `bot.py`: Main bot logic.
- `languages.py`: Multi-language support (English, Hindi, Bengali, etc.).
- `requirements.txt`: Python dependencies.
- `downloads/`: Temporary directory for media files.

## ⚖️ License

This project is for educational purposes. Please ensure compliance with platform terms of service when using automation features.
