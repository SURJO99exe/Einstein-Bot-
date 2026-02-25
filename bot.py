import yt_dlp
import discord
from discord.ext import commands as discord_commands
import os
import logging
import psutil
import subprocess
import threading
import time
import math
import subprocess
import shutil
import uuid
import json
import requests
import base64
import sqlite3
import asyncio
import asyncio
import uuid
import shutil
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask, render_template_string, request, jsonify

# Import multi-language support
from languages import detect_language, get_text, get_language_name, LANGUAGES

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
JSON2VIDEO_KEY = os.getenv("JSON2VIDEO_KEY")
SISIF_API_KEY = os.getenv("SISIF_API_KEY")
VEO3_API_KEY = os.getenv("VEO3_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
WEB_PORT = 18789  # Web interface port (same as OpenClaw)

# Global state for dashboard
active_users_set = {} # {user_id: {"username": str, "last_seen": timestamp, "lang": "en"}}
user_languages = {} # {user_id: "en"}
bot_logs = []
user_commands_history = []  # Store objects like {"user_id": 123, "command": "/start", "time": "..."}
remote_clients = {}  # {user_id: {"last_seen": timestamp, "pending_commands": [], "location": {"lat": 0, "lon": 0}}}
share_location_active = {} # {user_id: [target_chat_ids]}
cf_tunnel_process = None
cf_tunnel_url = None
bot_config = {
    "ai_enabled": True,
    "maintenance_mode": False,
    "logging_level": "INFO"
}

def add_to_logs(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    bot_logs.append(f"[{timestamp}] {message}")
    if len(bot_logs) > 100:
        bot_logs.pop(0)

# Flask app
app = Flask(__name__)

# Store bot application globally
bot_app = None

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def background_cleanup():
    """Periodically cleans up the downloads folder in the background"""
    download_dir = "d:/clow bot/downloads"
    while True:
        try:
            if os.path.exists(download_dir):
                current_time = time.time()
                for item in os.listdir(download_dir):
                    item_path = os.path.join(download_dir, item)
                    # Delete if older than 1 hour
                    if os.path.getmtime(item_path) < current_time - 3600:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                        logging.info(f"Background Cleanup: Removed {item}")
        except Exception as e:
            logging.error(f"Background Cleanup Error: {e}")
        
        time.sleep(3600)  # Run every hour

async def check_auth(update: Update):
    """Allows all users to use the bot (Restricted ID check disabled)"""
    return True

def escape_html(text: str) -> str:
    """Escapes HTML special characters for Telegram."""
    if not text:
        return ""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def escape_markdown(text: str, version: int = 1) -> str:
    """Escapes markdown special characters based on the version."""
    if not text:
        return ""
    if version == 1:
        # Legacy Markdown
        escape_chars = ['_', '*', '`', '[']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    else:
        # MarkdownV2
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text

async def setup_commands(application):
    """Set up the bot command menu in Telegram"""
    commands = [
        # System
        BotCommand("stop", "🛑 Stop all active operations"),
        BotCommand("clear", "🧹 Clear chat messages"),
        BotCommand("files", "📁 List workspace files"),
        
        # Phone Control
        BotCommand("phone", "📱 Control phone (flash, volume, etc)"),
        
        # Browser & Capture
        BotCommand("browser", "🌐 Browser control (screenshot, navigate)"),
        BotCommand("screenshot", "📸 Desktop or web screenshot"),
        
        # Search & AI
        BotCommand("search", "🔍 Real-time web search"),
        BotCommand("weather", "🌤️ Weather information"),
        BotCommand("ai", "🤖 Chat with OpenAI"),
        BotCommand("ollama", "🦙 Free local AI chat"),
        BotCommand("claude", "🧠 Chat with Claude AI"),
        BotCommand("smart", "🧠 AI Smart - Natural language command processor"),
        
        # Social Media
        BotCommand("facebook", "📘 Facebook page control"),
        BotCommand("youtube", "📺 YouTube channel control"),
        BotCommand("tiktok", "🎵 TikTok account control"),
        BotCommand("twitter", "🐦 Twitter/X posting"),
        BotCommand("whatsapp", "💬 WhatsApp Business API"),
        
        # Developer Tools
        BotCommand("github", "🐙 GitHub repository control"),
        BotCommand("gmail", "📧 Gmail email control"),
        BotCommand("discord", "💬 Send Discord message"),
        BotCommand("slack", "💼 Send Slack message"),
        
        # Media
        BotCommand("spotify", "🎵 Spotify music control"),
        
        # Productivity
        BotCommand("note", "📝 Notes manager (Obsidian-like)"),
        BotCommand("remind", "⏰ Reminders & tasks"),
        BotCommand("calendar", "📅 Calendar management"),
        
        # Travel
        BotCommand("flight", "✈️ Flight status & check-in"),
        
        # File Manager
        BotCommand("file", "📁 File management"),
        
        # Smart Home
        BotCommand("home", "🏠 Smart home control (Hue)"),
        
        # Utilities
        BotCommand("utils", "🛠️ Utilities (QR, password, news)"),
        BotCommand("thumb", "🖼️ AI Thumbnail Generator"),
        BotCommand("botprofile", "🤖 Manage bot profile & photo"),
        
        # Language
        BotCommand("language", "🌍 Change language / भाषा बदलें"),
        
        # AI Smart Command
        BotCommand("smart", "🧠 AI Smart - Natural language command processor"),
    ]
    
    await application.bot.set_my_commands(commands)
    print("📋 Command menu set up successfully!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    user_id = str(update.effective_user.id)
    lang = user_languages.get(user_id, 'en')
    
    # Set up command menu when user starts the bot
    await setup_commands(context.application)
    
    keyboard = [
        ['📊 Status', '📂 Files', '💻 CMD'],
        ['🌤️ Weather', '🔍 Search', '👨‍🔬 Einstein'],
        ['🌐 Browser', '📸 Capture', '🛠️ Utils'],
        ['📱 Phone', '📍 Share Loc', '📺 Media'],
        ['🔎 YT Search', '💬 Chat', '🐙 GitHub'],
        ['📧 Gmail', '📝 Notes', '⏰ Remind'],
        ['📅 Calendar', '✈️ Travel', '📁 Manager'],
        ['🏠 SmartHome', '💬 Discord', '🤖 AI Smart'],
        ['📖 Help']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = get_text('welcome', lang, web_port=f"http://127.0.0.1:{WEB_PORT}")
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='HTML',
        disable_web_page_preview=True
    )

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    
    user_id = str(update.effective_user.id)
    lang = user_languages.get(user_id, 'en')
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    # Visual status bars
    def get_bar(pct):
        filled = int(pct / 10)
        return '🟢' * filled + '⚪' * (10 - filled)

    status_msg = get_text('system_status', lang, cpu=cpu, ram=ram, disk=disk)
    await update.message.reply_text(status_msg, parse_mode='HTML')

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    
    try:
        files = os.listdir('.')
        files_str = "\n".join([f"📄 {f}" for f in files[:20]]) # Limit to 20 for now
        await update.message.reply_text(f"📂 **Files in current directory:**\n\n{files_str}", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ============== MULTI-TASK FEATURES ==============

async def get_weather(update: Update, city: str = None):
    """Get weather information with stylish Einstein flair"""
    user_id = str(update.effective_user.id)
    lang = user_languages.get(user_id, 'en')
    
    if not city:
        await update.message.reply_text(
            get_text('weather_usage', lang),
            parse_mode='HTML'
        )
        return
    
    try:
        # Try WeatherAPI.com (more reliable for current updates)
        weatherapi_key = os.getenv("WEATHER_API_KEY")
        if weatherapi_key and weatherapi_key != "your_weatherapi_key_here":
            url = f"http://api.weatherapi.com/v1/current.json?key={weatherapi_key}&q={city}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if response.status_code == 200:
                location = data['location']
                current = data['current']
                weather_info = (
                    f"🌤️ **Atmospheric Conditions: {location['name']}**\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🌡️ **Temperature:** `{current['temp_c']}°C`\n"
                    f"🌡️ **Feels like:** `{current['feelslike_c']}°C`\n"
                    f"💧 **Humidity:** `{current['humidity']}%`\n"
                    f"🌬️ **Wind Speed:** `{current['wind_kph']} km/h`\n"
                    f"☁️ **Condition:** `{current['condition']['text']}`\n\n"
                    f"👨‍🔬 *\"Look deep into nature, and then you will understand everything better.\"*"
                )
                await update.message.reply_text(weather_info, parse_mode='HTML')
                return
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                await update.message.reply_text(f"❌ **WeatherAPI Error:** `{error_msg}`", parse_mode='HTML')
                return
    except Exception as e:
        await update.message.reply_text(f"❌ **Meteorological Error:** `{str(e)}`", parse_mode='HTML')
        return
    
    # Demo mode if no APIs available
    await update.message.reply_text(
        f"🌤️ Weather for {city}\n\n"
        f"🌡️ Temperature: 28°C\n"
        f"💧 Humidity: 65%\n"
        f"🌬️ Wind: 12 km/h\n"
        f"☁️ Condition: Partly Cloudy\n\n"
        f"⚠️ Demo mode - Add API key to .env for real data:\n"
        f"• OpenWeatherMap: openweathermap.org\n"
        f"• WeatherAPI.com: weatherapi.com"
    )

async def search_web(update: Update, query: str = None):
    """Real-time web search using DuckDuckGo"""
    if not query:
        await update.message.reply_text("🔍 Web Search\n\nUsage: /search [your query]\nExample: /search latest tech news")
        return
    
    try:
        await update.message.reply_text(f"🔍 Searching for: {query}...")
        
        # Using DuckDuckGo HTML search (no API key needed)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('a', class_='result__a', limit=5)
            
            if results:
                search_results = "🔍 Search Results:\n\n"
                for i, result in enumerate(results, 1):
                    title = result.get_text(strip=True)
                    link = result.get('href', '')
                    search_results += f"{i}. {title}\n{link}\n\n"
                
                await update.message.reply_text(search_results[:4000])
            else:
                await update.message.reply_text("❌ No results found. Try a different query.")
        else:
            await update.message.reply_text("❌ Search failed. Please try again.")
    except Exception as e:
        await update.message.reply_text(f"❌ Search error: {str(e)}")

async def facebook_control(update: Update, action: str = None):
    """Facebook Page control features with Graph API integration"""
    token = os.getenv("FACEBOOK_PAGE_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")

    if not action:
        keyboard = [
            [InlineKeyboardButton("📊 Page Stats", callback_data='fb_stats')],
            [InlineKeyboardButton("📝 Create Post", callback_data='fb_post_prompt')],
            [InlineKeyboardButton("📸 Upload Photo", callback_data='fb_photo_prompt')],
            [InlineKeyboardButton("💬 Latest Comments", callback_data='fb_comments')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_text = "✅ **API Connected**" if token and len(token) > 20 else "❌ **API Not Configured**"
        
        await update.message.reply_text(
            "📘 **Einstein Facebook Controller**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 **Status:** {status_text}\n"
            f"🆔 **Page ID:** `{page_id if page_id else 'Not Set'}`\n\n"
            "👨‍🔬 *\"Everything is determined, the beginning as well as the end, by forces over which we have no control.\"*\n\n"
            "Choose an action from the menu below:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return

    if not token or len(token) < 20:
        await update.message.reply_text(
            "❌ **Facebook API Not Configured**\n\n"
            "Please add `FACEBOOK_PAGE_TOKEN` and `FACEBOOK_PAGE_ID` to your `.env` file.\n"
            "🔭 *Experiment cannot proceed without proper instrumentation.*",
            parse_mode='HTML'
        )
        return

    try:
        if action == "stats":
            # Fetch basic page stats
            url = f"https://graph.facebook.com/v19.0/{page_id}?fields=fan_count,followers_count,talking_about_count,name&access_token={token}"
            response = requests.get(url).json()
            
            if 'error' in response:
                raise Exception(response['error']['message'])
                
            stats_msg = (
                f"📊 **Facebook Page Statistics: {response.get('name')}**\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 **Followers:** `{response.get('followers_count', 0)}` \n"
                f"👍 **Page Likes:** `{response.get('fan_count', 0)}` \n"
                f"💬 **People Talking About:** `{response.get('talking_about_count', 0)}` \n\n"
                "✨ *Data synchronized with Graph API.*"
            )
            await update.message.reply_text(stats_msg, parse_mode='HTML')

        elif action == "post" and len(context.args) > 1:
            message = " ".join(context.args[1:])
            url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
            payload = {'message': message, 'access_token': token}
            response = requests.post(url, data=payload).json()
            
            if 'error' in response:
                raise Exception(response['error']['message'])
                
            await update.message.reply_text(
                f"✅ **Post Published Successfully!**\n"
                f"🆔 **Post ID:** `{response.get('id')}`\n\n"
                "👨‍🔬 *Thought manifest in the social sphere.*",
                parse_mode='HTML'
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ **Facebook Graph Error:**\n`{str(e)}`", parse_mode='HTML')

async def youtube_control(update: Update, action: str = None):
    """YouTube search, trending, and viral video browser"""
    if not action:
        keyboard = [
            [InlineKeyboardButton("🔥 Trending Now", callback_data='yt_trending')],
            [InlineKeyboardButton("🌍 Viral Worldwide", callback_data='yt_viral')],
            [InlineKeyboardButton("🔎 Search YouTube", callback_data='yt_search_prompt')],
            [InlineKeyboardButton("🎬 Video Player Info", callback_data='yt_player_help')],
            [InlineKeyboardButton("📊 Channel Stats", callback_data='yt_stats')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📺 **YouTube Explorer**\n"
            "━━━━━━━━━━━━━━━\n"
            "Browse trending videos, search, and more!\n\n"
            "**Commands:**\n"
            "/yt trending - Show trending videos\n"
            "/yt search [query] - Search videos\n"
            "/yt viral - Viral content",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return

async def get_youtube_trending(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
    """Fetch trending videos from YouTube"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or "your_youtube_api_key" in api_key:
        await update.callback_query.message.edit_text("❌ YouTube API Key missing in .env") if update.callback_query else await update.message.reply_text("❌ YouTube API Key missing in .env")
        return

    try:
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&chart=mostPopular&maxResults=5&regionCode=US&key={api_key}"
        response = requests.get(url)
        data = response.json()

        if 'items' in data:
            msg = "🔥 **Trending on YouTube**\n━━━━━━━━━━━━━━━\n\n"
            for item in data['items']:
                title = item['snippet']['title']
                channel = item['snippet']['channelTitle']
                video_id = item['id']
                views = item['statistics'].get('viewCount', '0')
                video_url = f"https://youtu.be/{video_id}"
                
                msg += f"🎬 **{title[:50]}...**\n"
                msg += f"👤 {channel} | 👁️ {int(views):,} views\n"
                msg += f"🔗 [Watch Now]({video_url})\n\n"
            
            if update.callback_query:
                await update.callback_query.message.edit_text(msg, parse_mode='HTML', disable_web_page_preview=False)
            else:
                await update.message.reply_text(msg, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Could not fetch trending videos.")
    except Exception as e:
        await update.message.reply_text(f"❌ YouTube Error: {str(e)}")

async def youtube_search(update: Update, query: str):
    """Search for videos on YouTube with interactive play buttons"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key == "your_youtube_api_key_here" or len(api_key) < 20:
        await update.message.reply_text("❌ YouTube API Key missing or invalid. Please check .env file.")
        return

    try:
        await update.message.reply_text(f"🔍 Searching for: {query}...")
        
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=5&q={requests.utils.quote(query)}&type=video&key={api_key}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if response.status_code != 200:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            await update.message.reply_text(f"❌ YouTube API Error: {error_msg}")
            return

        if 'items' in data and len(data['items']) > 0:
            await update.message.reply_text(f"🔎 **Top 5 Results for:** `{query}`", parse_mode='HTML')
            
            for item in data['items']:
                title = item['snippet']['title']
                video_id = item['id']['videoId']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                channel = item['snippet']['channelTitle']
                thumbnail_url = item['snippet']['thumbnails']['high']['url']
                
                keyboard = [
                    [
                        InlineKeyboardButton("🎵 Play Audio", callback_data=f"dl_audio_{video_id}"),
                        InlineKeyboardButton("🎥 Play Video", callback_data=f"dl_video_{video_id}")
                    ],
                    [
                        InlineKeyboardButton("🔗 Open YouTube", url=video_url)
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Format message with HTML
                caption = (
                    f"🎬 <b>{escape_html(title)}</b>\n"
                    f"👤 <b>Channel:</b> {escape_html(channel)}\n"
                    f"🔗 <a href='{video_url}'>Watch on YouTube</a>"
                )
                
                try:
                    await update.message.reply_photo(
                        photo=thumbnail_url,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    # Fallback if thumbnail fails
                    await update.message.reply_text(
                        caption,
                        reply_markup=reply_markup,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
        else:
            await update.message.reply_text("❌ No videos found for this query.")
    except Exception as e:
        await update.message.reply_text(f"❌ Search Error: {str(e)}")
        import traceback
        print(f"YouTube search error: {traceback.format_exc()}")

async def youtube_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /yt command - search YouTube and show results with play buttons"""
    try:
        # Check if API key exists
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key or api_key == "your_youtube_api_key_here" or len(api_key) < 20:
            await youtube_control(update, None)
            return

        if not context.args:
            await update.message.reply_text("📺 **YouTube Search**\n\nUsage: `/yt [search query]`\nExample: `/yt lofi hip hop` or click the button below.", parse_mode='HTML')
            await youtube_control(update, None)
            return

        query = " ".join(context.args)
        await youtube_search(update, query)
    except Exception as e:
        import traceback
        print(f"YouTube command error: {traceback.format_exc()}")

async def tiktok_control(update: Update, action: str = None):
    """TikTok account control features"""
    if not action:
        keyboard = [
            [InlineKeyboardButton("📊 Account Stats", callback_data='tt_stats')],
            [InlineKeyboardButton("🎵 Upload Video", callback_data='tt_upload')],
            [InlineKeyboardButton("💬 Comments", callback_data='tt_comments')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎵 TikTok Control\n\n"
            "Choose an action:",
            reply_markup=reply_markup
        )
        return
    
    await update.message.reply_text(
        "🎵 TikTok Control\n\n"
        "⚠️ Setup Required:\n"
        "1. TikTok Business Account\n"
        "2. Add API credentials to .env\n\n"
        "Features available:\n"
        "• 📊 Account analytics\n"
        "• 🎵 Video upload\n"
        "• 💬 Comment management\n"
        "• 📈 Trending sounds"
    )

async def phone_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control phone settings (Flash, Volume, etc.)"""
    if not await check_auth(update): return
    
    keyboard = [
        [
            InlineKeyboardButton("🔦 Flash ON", callback_data='phone_flash_on'),
            InlineKeyboardButton("🔦 Flash OFF", callback_data='phone_flash_off')
        ],
        [
            InlineKeyboardButton("🔊 Max Volume", callback_data='phone_vol_max'),
            InlineKeyboardButton("🔇 Mute", callback_data='phone_vol_mute')
        ],
        [
            InlineKeyboardButton("🎵 Play Siren", callback_data='phone_siren'),
            InlineKeyboardButton("⏹️ Stop All", callback_data='phone_stop')
        ],
        [
            InlineKeyboardButton("📍 Live Location", callback_data='phone_location'),
            InlineKeyboardButton("🔋 Battery Status", callback_data='phone_battery')
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data='phone_settings'),
            InlineKeyboardButton("📸 Front Cam", callback_data='phone_cam_front')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📱 **Einstein Phone Controller**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a command to control the device:\n\n"
        "👨‍🔬 *\"Everything is determined by forces over which we have no control.\"*",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Language selection command - supports multi-language interface"""
    if not context.args:
        # Show language selection menu
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
            [InlineKeyboardButton("🇧🇩 বাংলা (Bengali)", callback_data='lang_bn')],
            [InlineKeyboardButton("🇮🇳 हिन्दी (Hindi)", callback_data='lang_hi')],
            [InlineKeyboardButton("🇪🇸 Español (Spanish)", callback_data='lang_es')],
            [InlineKeyboardButton("🇸🇦 العربية (Arabic)", callback_data='lang_ar')],
            [InlineKeyboardButton("🇨🇳 中文 (Chinese)", callback_data='lang_zh')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌍 **Select Your Language / আপনার ভাষা নির্বাচন করুন / अपनी भाषा चुनें**\n\n"
            "Choose your preferred language for the bot interface:\n"
            "বট ইন্টারফেসের জন্য আপনার পছন্দের ভাষা বেছে নিন:\n"
            "बॉट इंटरफेस के लिए अपनी पसंदीदा भाषा चुनें:\n\n"
            "Current / বর্তমান / वर्तमान: 🏴󠁧󠁢󠁥󠁮󠁧󠁿 English",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    lang = context.args[0].lower()
    supported_langs = ['en', 'bn', 'hi', 'es', 'ar', 'zh']
    
    if lang in supported_langs:
        # Store user language preference (in a real app, store in database)
        lang_names = {
            'en': '🇬🇧 English',
            'bn': '🇧🇩 বাংলা',
            'hi': '🇮🇳 हिन्दी',
            'es': '🇪🇸 Español',
            'ar': '🇸🇦 العربية',
            'zh': '🇨🇳 中文'
        }
        
        welcome_msg = get_text('welcome', lang, web_port=f"http://127.0.0.1:{WEB_PORT}")
        
        await update.message.reply_text(
            f"✅ Language set to: {lang_names[lang]}\n\n"
            f"{welcome_msg}"
        )
    else:
        await update.message.reply_text(
            "⚠️ Unsupported language!\n\n"
            "Supported languages:\n"
            "🇬🇧 en - English\n"
            "🇧🇩 bn - Bengali\n"
            "🇮🇳 hi - Hindi\n"
            "🇪🇸 es - Spanish\n"
            "🇸🇦 ar - Arabic\n"
            "🇨🇳 zh - Chinese\n\n"
            "Usage: /language [code]\n"
            "Example: /language bn"
        )

async def tunnel_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start or stop the Cloudflare tunnel via Telegram command with custom link support"""
    if not await check_auth(update): return
    
    global cf_tunnel_process, cf_tunnel_url
    
    command = context.args[0].lower() if context.args else "status"
    target_url = context.args[1] if len(context.args) > 1 else f"http://localhost:{WEB_PORT}"
    
    if command == "start":
        # Check if same target is already running
        if cf_tunnel_process and cf_tunnel_url and cf_tunnel_url != "None":
            await update.message.reply_text(f"✅ **Tunnel already live!**\n🔗 {cf_tunnel_url}", parse_mode='HTML')
            return

        if cf_tunnel_process:
            try:
                cf_tunnel_process.terminate()
                cf_tunnel_process = None
                cf_tunnel_url = None
            except: pass
            
        try:
            # Start tunnel with ultra-fast flags
            cmd = ["cloudflared", "tunnel", "--url", target_url]
            cf_tunnel_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Instant acknowledgement
            await update.message.reply_text(f"🚀 **Einstein is calculating the secure path...** 🧪", parse_mode='HTML')
            
            def track_url(process, chat_id, target, bot_instance, loop_instance):
                global cf_tunnel_url
                import re
                try:
                    while True:
                        line = process.stdout.readline()
                        if not line: break
                        line_str = line.strip()
                        if not line_str: continue
                        
                        add_to_logs(f"CF: {line_str}")
                        
                        if ".trycloudflare.com" in line_str:
                            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line_str)
                            if match:
                                cf_tunnel_url = match.group(0)
                                # Instant delivery using loop.create_task
                                loop_instance.call_soon_threadsafe(
                                    lambda: loop_instance.create_task(
                                        bot_instance.send_message(
                                            chat_id=chat_id, 
                                            text=f"✅ **Tunnel Live!**\n🔗 {cf_tunnel_url}",
                                            parse_mode='HTML'
                                        )
                                    )
                                )
                                break
                except Exception as e:
                    add_to_logs(f"Tracking error: {e}")
                finally:
                    try: process.stdout.close()
                    except: pass

            import threading
            threading.Thread(
                target=track_url, 
                args=(cf_tunnel_process, update.effective_chat.id, target_url, context.bot, asyncio.get_event_loop()), 
                daemon=True
            ).start()
            
        except Exception as e:
            await update.message.reply_text(f"❌ **Error:** `{str(e)}`", parse_mode='HTML')
            
    elif command == "stop":
        if cf_tunnel_process:
            cf_tunnel_process.terminate()
            cf_tunnel_process = None
            cf_tunnel_url = None
            await update.message.reply_text("🛑 **Cloudflare Tunnel Stopped.**", parse_mode='HTML')
        else:
            await update.message.reply_text("⚠️ **No tunnel is currently running.**", parse_mode='HTML')
            
    else: # Status
        status = "🟢 Running" if cf_tunnel_process else "🔴 Offline"
        url = cf_tunnel_url if cf_tunnel_url else "None"
        await update.message.reply_text(
            f"☁️ **Cloudflare Tunnel Status**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Status:** {status}\n"
            f"🌐 **URL:** `{url}`\n\n"
            f"💡 *Use `/tunnel start` or `/tunnel stop` to control.*",
            parse_mode='HTML'
        )

async def stop_all_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop all active bot operations (Tunnel, Location sharing, Phone commands)"""
    if not await check_auth(update): return
    
    global cf_tunnel_process, cf_tunnel_url, share_location_active
    
    results = []
    
    # 1. Force Stop Cloudflare Tunnel
    if cf_tunnel_process:
        try:
            # Use taskkill on Windows for absolute termination
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(cf_tunnel_process.pid)], capture_output=True)
            else:
                cf_tunnel_process.terminate()
                cf_tunnel_process.kill()
            
            cf_tunnel_process = None
            cf_tunnel_url = None
            results.append("🛑 Cloudflare Tunnel Terminated")
        except Exception as e:
            add_to_logs(f"Stop Error (Tunnel): {e}")
            results.append("⚠️ Tunnel stop failed (Force killed instead)")
        
    # 2. Stop Location Sharing
    if share_location_active:
        share_location_active.clear()
        results.append("📍 All Location Sharing Stopped")
        
    # 3. Stop Remote Phone Actions (Queue stop for all clients)
    for user_id in remote_clients:
        remote_clients[user_id]["pending_commands"] = ["stop"]
    results.append("📱 Emergency Stop sent to all Remote Devices")
    
    # 4. Local stop (if running on Termux)
    if os.name != 'nt':
        try:
            subprocess.run(["termux-flashlight", "off"], capture_output=True)
            subprocess.run(["termux-volume", "music", "0"], capture_output=True)
            results.append("⚡ Local hardware neutralized")
        except: pass

    if not results:
        await update.message.reply_text("✨ **System is already idle.**", parse_mode='HTML')
    else:
        status_text = "\n".join([f"• {r}" for r in results])
        await update.message.reply_text(
            f"⚖️ **System-Wide Emergency Stop**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{status_text}\n\n"
            f"✨ *All processes have been forced to stop.*",
            parse_mode='HTML'
        )

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete recent messages in the chat (up to 100)"""
    if not await check_auth(update): return
    
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id
    
    try:
        # Get count from args, default to 100
        amount = 100
        if context.args and context.args[0].isdigit():
            amount = min(int(context.args[0]), 100)
        
        status_msg = await update.message.reply_text(f"🧹 **Cleaning up {amount} messages...**", parse_mode='HTML')
        
        deleted_count = 0
        # Attempt to delete messages one by one
        for i in range(amount + 1): # +1 to include the command itself
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id - i)
                deleted_count += 1
            except Exception:
                continue
        
        # Send a self-destructing confirmation
        final_msg = await context.bot.send_message(
            chat_id=chat_id, 
            text=f"✅ **Cleaned {deleted_count} messages!**", 
            parse_mode='HTML'
        )
        import asyncio
        await asyncio.sleep(3)
        await final_msg.delete()
        
    except Exception as e:
        await update.message.reply_text(f"❌ **Clear Error:** `{str(e)}`", parse_mode='HTML')

async def list_workspace_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all files in the current workspace"""
    if not await check_auth(update): return
    
    try:
        files = os.listdir(".")
        file_list = []
        for f in files:
            size = os.path.getsize(f)
            if os.path.isdir(f):
                file_list.append(f"📁 <b>{f}/</b>")
            else:
                kb_size = size / 1024
                file_list.append(f"📄 {f} (<i>{kb_size:.1f} KB</i>)")
        
        response = "📂 <b>Workspace Files:</b>\n" + "━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(file_list)
        await update.message.reply_text(response, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Error listing files: {str(e)}")

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands and bot capabilities"""
    help_text = (
        "🧠 <b>Einstein OS - Command Lab</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>🚀 Core Commands:</b>\n"
        "• /start - Wake up Einstein\n"
        "• /help - Show this manual\n"
        "• /stop - Emergency System Stop\n\n"
        "<b>☁️ Networking:</b>\n"
        "• /tunnel [start/stop/status] [url] - HTTPS Tunneling\n\n"
        "<b>📁 Data & Files:</b>\n"
        "• /files - List workspace contents\n"
        "• Send any URL - Instant Video/Media Download\n\n"
        "<b>📱 Phone Control:</b>\n"
        "• /phone - Remote Device Dashboard\n"
        "• /location - Share Live GPS\n\n"
        "<b>🧬 Intelligence:</b>\n"
        "• Just chat - Einstein AI Thinking\n"
        "• /image [prompt] - Generate AI Art\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📥 @alberteinstein247_bot"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wake up Einstein and show the custom command keyboard"""
    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_id="status"), InlineKeyboardButton("📂 Files", callback_data="files"), InlineKeyboardButton("💻 CMD", callback_id="cmd")],
        [InlineKeyboardButton("🌤️ Weather", callback_id="weather"), InlineKeyboardButton("🔍 Search", callback_id="search"), InlineKeyboardButton("👨‍🔬 Einstein", callback_id="ai")],
        [InlineKeyboardButton("🌐 Browser", callback_id="browser"), InlineKeyboardButton("📸 Capture", callback_id="capture"), InlineKeyboardButton("🛠️ Utils", callback_id="utils")],
        [InlineKeyboardButton("📱 Social", callback_id="social"), InlineKeyboardButton("📺 Media", callback_id="media"), InlineKeyboardButton("🔎 YT Search", callback_id="yt")],
        [InlineKeyboardButton("☁️ Tunnel", callback_data="tunnel_menu"), InlineKeyboardButton("🛑 STOP", callback_data="stop_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧠 <b>Einstein OS - Ready for Input</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to the laboratory. Select a module below or use /help for all commands.",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "files":
        await list_workspace_files(update, context)
    elif data == "tunnel_menu":
        await update.effective_message.reply_text(
            "☁️ <b>Tunnel Control</b>\n"
            "• <code>/tunnel start</code> - Start default tunnel\n"
            "• <code>/tunnel stop</code> - Close tunnel",
            parse_mode='HTML'
        )
    elif data == "stop_all":
        await stop_all_actions(update, context)
    
    # Helper to create mock update from query for command reuse
    def mock_update_from_query(q):
        class MockUpdate:
            def __init__(self, msg):
                self.message = msg
                self.effective_user = msg.from_user
                self.effective_chat = msg.chat
                self.callback_query = q
        return MockUpdate(q.message)
    
    # YouTube actions
    if data == 'yt_trending':
        await get_youtube_trending(update)
        return
    elif data == 'yt_viral':
        await get_youtube_trending(update) # Reuse for now
        return
    elif data == 'yt_search_prompt':
        await query.message.reply_text("🔎 Send me your search query using `/yt [your search]`\nExample: `/yt Atif Aslam`")
        return
    elif data == 'yt_player_help':
        await query.message.reply_text("🎬 **Video Player**\n\nSimply paste a YouTube link or use `/video [URL]` to play and download any video!")
        return
    elif data == 'yt_stats':
        await youtube_control(update.callback_query, action="stats")
        return
    
    # Facebook actions
    elif data == 'fb_stats':
        await facebook_control(mock_update_from_query(query), action="stats")
        return
    elif data == 'fb_post_prompt':
        await query.message.reply_text("📝 To create a post, use: `/fb_post [your message]`")
        return
    elif data == 'fb_comments':
        await query.message.reply_text("💬 This feature is being calibrated with the Graph API.")
        return

    elif data.startswith('dl_audio_'):
        try:
            video_id = data.replace('dl_audio_', '')
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Send a message to show we're processing
            await query.message.reply_text("🎵 Downloading audio... Please wait")
            
            # Create MockUpdate to simulate Update object
            class MockUpdate:
                def __init__(self, msg):
                    self.message = msg
                    self.effective_user = msg.from_user
                    self.effective_chat = msg.chat
            
            # Create MockContext
            class MockContext:
                def __init__(self, args, app):
                    self.args = args
                    self._app = app
                    self.bot = app.bot
                @property
                def application(self): return self._app
            
            mock_update = MockUpdate(query.message)
            mock_ctx = MockContext([video_url], context.application)
            await music_downloader(mock_update, mock_ctx)
        except Exception as e:
            import traceback
            error_msg = f"Audio error: {str(e)}\n{traceback.format_exc()[:500]}"
            print(error_msg)
            await query.message.reply_text(f"❌ Error playing audio: {str(e)[:200]}")
        return
    elif data.startswith('dl_video_'):
        try:
            video_id = data.replace('dl_video_', '')
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Send a message to show we're processing
            await query.message.reply_text("🎥 Downloading video... Please wait")
            
            # Create MockUpdate to simulate Update object
            class MockUpdate:
                def __init__(self, msg):
                    self.message = msg
                    self.effective_user = msg.from_user
                    self.effective_chat = msg.chat
            
            # Create MockContext
            class MockContext:
                def __init__(self, args, app):
                    self.args = args
                    self._app = app
                    self.bot = app.bot
                @property
                def application(self): return self._app
            
            mock_update = MockUpdate(query.message)
            mock_ctx = MockContext([video_url], context.application)
            await video_downloader(mock_update, mock_ctx)
        except Exception as e:
            import traceback
            error_msg = f"Video error: {str(e)}\n{traceback.format_exc()[:500]}"
            print(error_msg)
            await query.message.reply_text(f"❌ Error playing video: {str(e)[:200]}")
        return
    
    if data.startswith('lang_'):
        lang = data.split('_')[1]
        lang_names = {
            'en': '🇬🇧 English',
            'bn': '🇧🇩 বাংলা',
            'hi': '🇮🇳 हिन्दी',
            'es': '🇪🇸 Español',
            'ar': '🇸🇦 العربية',
            'zh': '🇨🇳 中文'
        }
        
        welcome_msg = get_text('welcome', lang, web_port=f"http://127.0.0.1:{WEB_PORT}")
        
        await query.edit_message_text(
            f"✅ Language changed to: {lang_names[lang]}\n\n"
            f"{welcome_msg}"
        )
        return

    # Phone control actions
    elif data.startswith('phone_'):
        action = data.replace('phone_', '')
        user_id = str(query.from_user.id)
        
        # Initialize remote client if not exists
        if user_id not in remote_clients:
            remote_clients[user_id] = {"last_seen": 0, "pending_commands": [], "location": {"lat": 0, "lon": 0}}
        
        # Ensure pending_commands is a list and add the action
        if "pending_commands" not in remote_clients[user_id]:
            remote_clients[user_id]["pending_commands"] = []
        remote_clients[user_id]["pending_commands"].append(action)
        
        # Log for debugging
        add_to_logs(f"Command '{action}' queued for user {user_id}")
        
        status_text = ""
        command_result = None
        
        # Fallback: Try to execute locally if bot is running on the device itself
        try:
            if action == "flash_on":
                status_text = "🔦 Command sent: Turn Flash ON"
                if os.name != 'nt': # Android/Termux
                    subprocess.run(["termux-flashlight", "on"], check=True)
                    command_result = "✅ Flash turned ON (Local)"
            elif action == "flash_off":
                status_text = "🔦 Command sent: Turn Flash OFF"
                if os.name != 'nt':
                    subprocess.run(["termux-flashlight", "off"], check=True)
                    command_result = "✅ Flash turned OFF (Local)"
            elif action == "vol_max":
                status_text = "🔊 Command sent: Set Volume to MAX"
                if os.name != 'nt':
                    subprocess.run(["termux-volume", "music", "15"], check=True)
                    command_result = "✅ Volume set to MAX (Local)"
            elif action == "vol_mute":
                status_text = "🔇 Command sent: Mute Device"
                if os.name != 'nt':
                    subprocess.run(["termux-volume", "music", "0"], check=True)
                    command_result = "✅ Volume MUTED (Local)"
            elif action == "siren":
                status_text = "🎵 Command sent: Play Siren 🚨"
            elif action == "stop":
                status_text = "⏹️ Command sent: Stop All Actions"
            elif action == "location":
                status_text = "📍 Command sent: Request Live Location"
                if os.name != 'nt':
                    # Try to get location locally as well
                    try:
                        res = subprocess.run(["termux-location"], capture_output=True, text=True)
                        if res.returncode == 0:
                            loc = json.loads(res.stdout)
                            await context.bot.send_location(chat_id=query.message.chat_id, latitude=loc['latitude'], longitude=loc['longitude'])
                            command_result = "📍 Location Shared (Local)"
                    except: pass
            elif action == "cam_front":
                status_text = "📸 Command sent: Capture Front Camera"
            elif action == "battery":
                status_text = "🔋 Command sent: Request Battery Status"
                import psutil
                battery = psutil.sensors_battery()
                if battery:
                    command_result = f"🔋 Battery: {battery.percent}% (Local)"
            elif action == "settings":
                status_text = "⚙️ Command sent: Open Settings"
        except Exception as e:
            add_to_logs(f"Local execution failed for {action}: {e}")

        final_msg = f"📱 **Remote Phone Command Sent**\n━━━━━━━━━━━━━━━━━━━━━\n👤 **Target Device:** User ID `{user_id}`\n⚡ **Action:** {status_text}"
        if command_result:
            final_msg += f"\n\n{command_result}"
        else:
            final_msg += f"\n\n⏳ *Waiting for the device to sync...*"

        await query.message.reply_text(final_msg, parse_mode='HTML')
        return

async def ai_chat(update: Update, message: str = None):
    """AI chat using OpenAI, Ollama (local), or demo mode"""
    if not message:
        await update.message.reply_text(
            "🤖 AI Chat\n\n"
            "Usage: /ai [your question]\n"
            "Example: /ai Explain quantum physics\n\n"
            "Powered by: OpenAI or Ollama (local AI)"
        )
        return
    
    try:
        await update.message.reply_text("🤖 Thinking...")
        
        # Check for OpenAI API key
        openai_key = os.getenv("OPENAI_API_KEY")
        use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
        
        if use_ollama:
            # Use Ollama (local AI)
            try:
                ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": ollama_model,
                        "prompt": message,
                        "stream": False
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "No response from Ollama")
                    await update.message.reply_text(f"👨‍🔬 **Einstein:**\n\n{answer[:4000]}")
                    return
                else:
                    raise Exception(f"Ollama error: {response.status_code}")
            except Exception as e:
                # Fall back to demo mode if Ollama fails
                print(f"Ollama error: {e}")
                pass
        
        if openai_key and openai_key != "your_openai_api_key_here":
            try:
                # Use OpenAI API
                import openai
                client = openai.OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": message}]
                )
                answer = response.choices[0].message.content
                await update.message.reply_text(f"🤖 OpenAI:\n\n{answer[:4000]}")
                return
            except Exception as e:
                error_msg = str(e)
                if "quota" in error_msg.lower() or "429" in error_msg:
                    await update.message.reply_text(
                        "⚠️ OpenAI quota exceeded!\n\n"
                        "Switching to Ollama (local AI)...\n"
                        "Use /ollama [message] for local AI chat"
                    )
                    return
                else:
                    raise e
        
        # Demo mode - simple responses
        responses = {
            "hello": "👋 Hello! How can I help you today?",
            "hi": "👋 Hi there! What can I do for you?",
            "weather": "🌤️ Use /weather [city] to check weather!",
            "time": f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        }
        answer = responses.get(message.lower(), 
            f"🤖 AI Mode (Demo)\n\nYou asked: {message}\n\n"
            f"For full AI responses:\n"
            f"1. Add OPENAI_API_KEY to .env for OpenAI\n"
            f"2. Or install Ollama for free local AI\n"
            f"   Download: https://ollama.com")
        
        await update.message.reply_text(answer[:4000])
        
    except Exception as e:
        await update.message.reply_text(f"❌ AI error: {str(e)}")

# ============== OPENCLAW FEATURES ==============

async def browser_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browser automation using Playwright"""
    if not context.args:
        await update.message.reply_text(
            "🌐 Browser Control\n\n"
            "Commands:\n"
            "/browser screenshot [url] - Take screenshot\n"
            "/browser navigate [url] - Navigate to URL\n"
            "/browser click [selector] - Click element\n"
            "/browser type [selector] [text] - Type text\n"
            "/browser scroll - Scroll page\n"
            "Example: /browser screenshot https://google.com"
        )
        return
    
    action = context.args[0].lower()
    
    try:
        from playwright.sync_api import sync_playwright
        
        await update.message.reply_text(f"🌐 Browser: {action}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            if action == "screenshot":
                url = context.args[1] if len(context.args) > 1 else "https://google.com"
                page.goto(url)
                screenshot_path = f"d:/clow bot/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_path, full_page=True)
                browser.close()
                
                # Send screenshot
                await update.message.reply_photo(open(screenshot_path, 'rb'), caption=f"📸 Screenshot of {url}")
                os.remove(screenshot_path)
                
            elif action == "navigate":
                url = context.args[1] if len(context.args) > 1 else "https://google.com"
                page.goto(url)
                title = page.title()
                browser.close()
                await update.message.reply_text(f"🌐 Navigated to: {title}\n{url}")
                
            elif action == "click":
                selector = context.args[1] if len(context.args) > 1 else "button"
                page.click(selector)
                browser.close()
                await update.message.reply_text(f"🖱️ Clicked: {selector}")
                
            elif action == "type":
                if len(context.args) >= 3:
                    selector = context.args[1]
                    text = " ".join(context.args[2:])
                    page.fill(selector, text)
                    browser.close()
                    await update.message.reply_text(f"⌨️ Typed into {selector}")
                else:
                    await update.message.reply_text("❌ Usage: /browser type [selector] [text]")
                    
            elif action == "scroll":
                page.evaluate("window.scrollBy(0, 500)")
                browser.close()
                await update.message.reply_text("📜 Scrolled down")
                
            else:
                browser.close()
                await update.message.reply_text("❌ Unknown browser action")
                
    except Exception as e:
        await update.message.reply_text(f"❌ Browser error: {str(e)}")

async def take_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick screenshot of desktop or URL"""
    try:
        if context.args:
            # Screenshot of URL
            url = context.args[0]
            await browser_control(update, type('Context', (), {'args': ['screenshot', url]})())
        else:
            # Desktop screenshot
            await update.message.reply_text("📸 Taking desktop screenshot...")
            screenshot_path = f"d:/clow bot/desktop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Use PIL for screenshot
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            screenshot.save(screenshot_path)
            
            await update.message.reply_photo(open(screenshot_path, 'rb'), caption="📸 Desktop Screenshot")
            os.remove(screenshot_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Screenshot error: {str(e)}")

def get_github_headers():
    """Helper to rotate between multiple GitHub tokens if one fails or hits rate limit"""
    tokens = [os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_TOKEN_2")]
    valid_tokens = [t for t in tokens if t and t != "your_token_here" and t != "your_second_github_token_here"]
    
    if not valid_tokens:
        return None
    
    # Try first token, if rate limited or fails, logic in github_control will handle retry
    token = valid_tokens[0]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

async def github_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GitHub repository control with multi-token support"""
    if not context.args:
        await update.message.reply_text(
            "🐙 **Einstein GitHub Architect**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Commands:\n"
            "• `/github website [name]` - 🚀 **Auto-build & Deploy Website**\n"
            "• `/github repos` - 📂 List your repositories\n"
            "• `/github create [name]` - 🆕 Create new repository\n"
            "• `/github delete [repo]` - 🗑️ Delete repository\n"
            "• `/github rename [old_name] [new_name]` - 📝 Rename repository\n"
            "• `/github stats [repo]` - 📊 View repository statistics\n"
            "• `/github profile` - 👤 View your GitHub profile\n"
            "• `/github issues [repo]` - 🐛 Manage issues\n"
            "• `/github clone [url]` - 📥 Clone repository\n\n"
            "👨‍🔬 *\"Genius is 1% inspiration and 99% automated deployment.\"*",
            parse_mode='HTML'
        )
        return
    
    action = context.args[0].lower()
    headers = get_github_headers()
    
    if not headers:
        await update.message.reply_text(
            "🐙 GitHub Control\n\n"
            "⚠️ Setup Required:\n"
            "1. Get GitHub Personal Access Token\n"
            "2. Add to .env: GITHUB_TOKEN=your_token\n\n"
            "Features:\n"
            "• 📂 List repositories\n"
            "• 🆕 Create repositories\n"
            "• 🐛 Manage issues\n"
            "• 📥 Clone repositories\n"
            "• 📊 View commit history"
        )
        return
    
    try:
        # Existing logic using headers
        
        if action == "website" and len(context.args) > 1:
            repo_name = context.args[1]
            await update.message.reply_text(f"🚀 **Einstein Web Architect** is designing your site: `{repo_name}`...", parse_mode='HTML')
            
            # 1. Create Repository
            create_data = {"name": repo_name, "private": False, "auto_init": True}
            create_resp = requests.post("https://api.github.com/user/repos", headers=headers, json=create_data)
            
            if create_resp.status_code != 201:
                await update.message.reply_text(f"❌ Failed to create repo: {create_resp.json().get('message')}")
                return

            user_data = requests.get("https://api.github.com/user", headers=headers).json()
            username = user_data['login']
            
            # 2. Prepare Website Files (Einstein Theme)
            index_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{repo_name} - Einstein System</title>
    <style>
        body {{ font-family: sans-serif; background: #121212; color: white; text-align: center; padding: 50px; }}
        .card {{ background: #1e1e1e; padding: 30px; border-radius: 15px; display: inline-block; border: 1px solid #6c5ce7; }}
        h1 {{ color: #a29bfe; }}
        p {{ font-style: italic; color: #888; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>⚛️ Einstein System Web</h1>
        <hr>
        <h2>Welcome to {repo_name}</h2>
        <p>"Logic will get you from A to Z; imagination will get you everywhere."</p>
        <div style="margin-top: 20px; font-weight: bold; color: #00b894;">DEPLOAYED SUCCESSFULLY</div>
    </div>
</body>
</html>"""
            
            # 3. Commit index.html
            file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/index.html"
            file_data = {
                "message": "Initialize Einstein Website",
                "content": base64.b64encode(index_html.encode()).decode(),
                "branch": "main"
            }
            requests.put(file_url, headers=headers, json=file_data)
            
            # 4. Enable GitHub Pages
            pages_url = f"https://api.github.com/repos/{username}/{repo_name}/pages"
            pages_data = {"source": {"branch": "main", "path": "/"}}
            headers_pages = headers.copy()
            headers_pages["Accept"] = "application/vnd.github.switcheroo-preview+json" # Required for pages API
            
            requests.post(pages_url, headers=headers_pages, json=pages_data)
            
            site_url = f"https://{username}.github.io/{repo_name}/"
            await update.message.reply_text(
                f"✅ **Website Created & Deployed!**\n\n"
                f"📂 **Repo:** `github.com/{username}/{repo_name}`\n"
                f"🌐 **Live URL:** {site_url}\n\n"
                f"👨‍🔬 *\"Genius is 1% inspiration and 99% automated deployment.\"*",
                parse_mode='HTML'
            )
            
        elif action == "delete" and len(context.args) > 1:
            repo_name = context.args[1]
            user_data = requests.get("https://api.github.com/user", headers=headers).json()
            username = user_data['login']
            
            delete_url = f"https://api.github.com/repos/{username}/{repo_name}"
            response = requests.delete(delete_url, headers=headers)
            
            if response.status_code == 204:
                await update.message.reply_text(f"🗑️ **Repository Deleted:** `{repo_name}` successfully removed from existence.", parse_mode='HTML')
            else:
                await update.message.reply_text(f"❌ Failed to delete repo: {response.json().get('message', 'Unknown error')}")

        elif action == "rename" and len(context.args) > 2:
            old_name = context.args[1]
            new_name = context.args[2]
            user_data = requests.get("https://api.github.com/user", headers=headers).json()
            username = user_data['login']
            
            rename_url = f"https://api.github.com/repos/{username}/{old_name}"
            data = {"name": new_name}
            response = requests.patch(rename_url, headers=headers, json=data)
            
            if response.status_code == 200:
                await update.message.reply_text(f"📝 **Repository Renamed:** `{old_name}` is now `{new_name}`.", parse_mode='HTML')
            else:
                await update.message.reply_text(f"❌ Failed to rename repo: {response.json().get('message', 'Unknown error')}")

        elif action == "stats" and len(context.args) > 1:
            repo_name = context.args[1]
            user_data = requests.get("https://api.github.com/user", headers=headers).json()
            username = user_data['login']
            
            stats_url = f"https://api.github.com/repos/{username}/{repo_name}"
            response = requests.get(stats_url, headers=headers).json()
            
            if 'name' in response:
                stats_text = (
                    f"📊 **Statistics for** `{repo_name}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⭐ **Stars:** `{response['stargazers_count']}`\n"
                    f"🍴 **Forks:** `{response['forks_count']}`\n"
                    f"👁️ **Watchers:** `{response['watchers_count']}`\n"
                    f"🐛 **Open Issues:** `{response['open_issues_count']}`\n"
                    f"📅 **Created:** `{response['created_at'][:10]}`\n"
                    f"🕒 **Last Update:** `{response['updated_at'][:10]}`"
                )
                await update.message.reply_text(stats_text, parse_mode='HTML')
            else:
                await update.message.reply_text(f"❌ Could not find stats for `{repo_name}`.")

        elif action == "profile":
            user_data = requests.get("https://api.github.com/user", headers=headers).json()
            profile_text = (
                f"👤 **GitHub Profile:** `{user_data['login']}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏢 **Company:** `{user_data.get('company', 'None')}`\n"
                f"📍 **Location:** `{user_data.get('location', 'Global')}`\n"
                f"📂 **Public Repos:** `{user_data['public_repos']}`\n"
                f"👥 **Followers:** `{user_data['followers']}`\n"
                f"✨ **Bio:** _{user_data.get('bio', 'No bio set.')}_"
            )
            await update.message.reply_text(profile_text, parse_mode='HTML')

        elif action == "repos":
            response = requests.get("https://api.github.com/user/repos", headers=headers)
            repos = response.json()
            repo_list = "🐙 Your Repositories:\n\n"
            for repo in repos[:10]:
                repo_list += f"• {repo['name']} - {repo['description'] or 'No description'}\n"
            await update.message.reply_text(repo_list[:4000])
            
        elif action == "create" and len(context.args) > 1:
            repo_name = context.args[1]
            data = {"name": repo_name, "private": False}
            response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
            if response.status_code == 201:
                await update.message.reply_text(f"✅ Repository created: {repo_name}")
            else:
                await update.message.reply_text(f"❌ Error: {response.json().get('message', 'Unknown error')}")
                
        else:
            await update.message.reply_text("🐙 GitHub command executed")
            
    except Exception as e:
        await update.message.reply_text(f"❌ GitHub error: {str(e)}")

async def twitter_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Twitter/X posting and control"""
    if not context.args:
        await update.message.reply_text(
            "🐦 Twitter/X Control\n\n"
            "Commands:\n"
            "/twitter post [text] - Post tweet\n"
            "/twitter timeline - View timeline\n"
            "/twitter search [query] - Search tweets\n\n"
            "⚠️ Add Twitter API keys to .env"
        )
        return
    
    action = context.args[0].lower()
    
    await update.message.reply_text(
        "🐦 Twitter/X Control\n\n"
        "⚠️ Setup Required:\n"
        "1. Twitter Developer Account\n"
        "2. Add API keys to .env:\n"
        "   TWITTER_API_KEY=xxx\n"
        "   TWITTER_API_SECRET=xxx\n"
        "   TWITTER_ACCESS_TOKEN=xxx\n"
        "   TWITTER_ACCESS_SECRET=xxx\n\n"
        "Features:\n"
        "• 📝 Post tweets\n"
        "• 📊 View timeline\n"
        "• 🔍 Search tweets\n"
        "• 💬 Reply to tweets\n"
        "• ❤️ Like/Retweet"
    )

async def gmail_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gmail email control"""
    if not context.args:
        await update.message.reply_text(
            "📧 Gmail Control\n\n"
            "Commands:\n"
            "/gmail inbox - Check inbox\n"
            "/gmail send [to] [subject] [body] - Send email\n"
            "/gmail search [query] - Search emails\n\n"
            "⚠️ Add Gmail credentials to .env"
        )
        return
    
    await update.message.reply_text(
        "📧 Gmail Control\n\n"
        "⚠️ Setup Required:\n"
        "1. Enable Gmail API in Google Cloud\n"
        "2. Add credentials to .env\n\n"
        "Features:\n"
        "• 📥 Read emails\n"
        "• 📤 Send emails\n"
        "• 🔍 Search emails\n"
        "• 🏷️ Manage labels\n"
        "• 📎 Attachments"
    )

async def spotify_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Spotify music control"""
    if not context.args:
        await update.message.reply_text(
            "🎵 Spotify Control\n\n"
            "Commands:\n"
            "/spotify play - Resume playback\n"
            "/spotify pause - Pause\n"
            "/spotify next - Next track\n"
            "/spotify prev - Previous track\n"
            "/spotify search [song] - Search music\n"
            "/spotify current - Now playing\n\n"
            "⚠️ Add Spotify credentials to .env"
        )
        return
    
    action = context.args[0].lower()
    
    await update.message.reply_text(
        "🎵 Spotify Control\n\n"
        "⚠️ Setup Required:\n"
        "1. Spotify Developer Account\n"
        "2. Add to .env:\n"
        "   SPOTIFY_CLIENT_ID=xxx\n"
        "   SPOTIFY_CLIENT_SECRET=xxx\n"
        "   SPOTIFY_REFRESH_TOKEN=xxx\n\n"
        "Features:\n"
        "• ▶️ Play/Pause/Skip\n"
        "• 🔍 Search tracks\n"
        "• 📋 Manage playlists\n"
        "• 🔊 Volume control\n"
        "• 📊 View queue"
    )

async def notes_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsidian-like notes management"""
    notes_dir = "d:/clow bot/notes"
    os.makedirs(notes_dir, exist_ok=True)
    
    if not context.args:
        # List all notes
        try:
            notes = [f for f in os.listdir(notes_dir) if f.endswith('.md')]
            if notes:
                notes_list = "📝 Your Notes:\n\n"
                for i, note in enumerate(notes, 1):
                    notes_list += f"{i}. {note[:-3]}\n"
                await update.message.reply_text(notes_list)
            else:
                await update.message.reply_text("📝 No notes found. Create one with:\n/note create [title] [content]")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    action = context.args[0].lower()
    
    try:
        if action == "create" and len(context.args) >= 3:
            title = context.args[1]
            content = " ".join(context.args[2:])
            filename = f"{notes_dir}/{title.replace(' ', '_')}.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(content)
            
            await update.message.reply_text(f"✅ Note created: {title}")
            
        elif action == "read" and len(context.args) >= 2:
            title = context.args[1]
            filename = f"{notes_dir}/{title.replace(' ', '_')}.md"
            
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                await update.message.reply_text(f"📝 {title}:\n\n{content[:4000]}")
            else:
                await update.message.reply_text(f"❌ Note not found: {title}")
                
        elif action == "delete" and len(context.args) >= 2:
            title = context.args[1]
            filename = f"{notes_dir}/{title.replace(' ', '_')}.md"
            
            if os.path.exists(filename):
                os.remove(filename)
                await update.message.reply_text(f"🗑️ Note deleted: {title}")
            else:
                await update.message.reply_text(f"❌ Note not found: {title}")
                
        elif action == "list":
            notes = [f[:-3] for f in os.listdir(notes_dir) if f.endswith('.md')]
            notes_list = "📝 Your Notes:\n\n" + "\n".join(notes) if notes else "No notes found."
            await update.message.reply_text(notes_list[:4000])
            
        else:
            await update.message.reply_text(
                "📝 Notes Manager\n\n"
                "Commands:\n"
                "/note create [title] [content]\n"
                "/note read [title]\n"
                "/note delete [title]\n"
                "/note list"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Notes error: {str(e)}")

async def reminders_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Task and reminder management"""
    reminders_file = "d:/clow bot/reminders.json"
    
    if not context.args:
        await update.message.reply_text(
            "⏰ Reminders Manager\n\n"
            "Commands:\n"
            "/remind add [time] [message] - Add reminder\n"
            "/remind list - View all reminders\n"
            "/remind delete [id] - Delete reminder\n\n"
            "Example: /remind add 10m Meeting with team"
        )
        return
    
    action = context.args[0].lower()
    
    try:
        # Load reminders
        if os.path.exists(reminders_file):
            with open(reminders_file, 'r') as f:
                reminders = json.load(f)
        else:
            reminders = []
        
        if action == "add" and len(context.args) >= 3:
            time_str = context.args[1]
            message = " ".join(context.args[2:])
            
            reminder = {
                "id": len(reminders) + 1,
                "time": time_str,
                "message": message,
                "created": datetime.now().isoformat(),
                "done": False
            }
            reminders.append(reminder)
            
            with open(reminders_file, 'w') as f:
                json.dump(reminders, f, indent=2)
            
            await update.message.reply_text(f"⏰ Reminder set: {message} in {time_str}")
            
        elif action == "list":
            if reminders:
                reminder_list = "⏰ Your Reminders:\n\n"
                for r in reminders:
                    status = "✅" if r['done'] else "⏳"
                    reminder_list += f"{status} #{r['id']}: {r['message']} ({r['time']})\n"
                await update.message.reply_text(reminder_list[:4000])
            else:
                await update.message.reply_text("⏰ No reminders set.")
                
        elif action == "delete" and len(context.args) >= 2:
            rid = int(context.args[1])
            reminders = [r for r in reminders if r['id'] != rid]
            
            with open(reminders_file, 'w') as f:
                json.dump(reminders, f, indent=2)
            
            await update.message.reply_text(f"🗑️ Reminder #{rid} deleted")
            
        else:
            await update.message.reply_text(
                "⏰ Reminders Manager\n\n"
                "/remind add [time] [message]\n"
                "/remind list\n"
                "/remind delete [id]"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Reminder error: {str(e)}")

async def smarthome_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smart home (Philips Hue) control"""
    if not context.args:
        await update.message.reply_text(
            "🏠 Smart Home Control\n\n"
            "Commands:\n"
            "/home lights on - Turn on lights\n"
            "/home lights off - Turn off lights\n"
            "/home color [color] - Change light color\n"
            "/home brightness [0-100] - Set brightness\n\n"
            "⚠️ Add Hue Bridge IP to .env"
        )
        return
    
    await update.message.reply_text(
        "🏠 Smart Home Control\n\n"
        "⚠️ Setup Required:\n"
        "1. Philips Hue Bridge\n"
        "2. Add to .env:\n"
        "   HUE_BRIDGE_IP=192.168.x.x\n"
        "   HUE_USERNAME=your_username\n\n"
        "Features:\n"
        "• 💡 Light on/off\n"
        "• 🎨 Color control\n"
        "• 🔆 Brightness\n"
        "• 📋 Room control\n"
        "• ⏰ Schedules"
    )

async def calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calculator - evaluate math expressions safely"""
    if not context.args:
        await update.message.reply_text(
            "🧮 **Einstein Mathematical Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Usage: `/calc [expression]`\n\n"
            "**Scientific Examples:**\n"
            "• `5 + 3 * 2`\n"
            "• `sqrt(16) * pi`\n"
            "• `2 ** 8` (Power)\n\n"
            "✨ *\"Pure mathematics is, in its way, the poetry of logical ideas.\"*",
            parse_mode='HTML'
        )
        return
    
    expression = " ".join(context.args)
    
    try:
        import math
        allowed_names = {
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'tan': math.tan, 'log': math.log, 'log10': math.log10,
            'pi': math.pi, 'e': math.e, 'abs': abs, 'round': round, 'pow': pow
        }
        
        expression = expression.replace('^', '**')
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        
        await update.message.reply_text(
            f"🧪 **Calculation Result**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 **Input:** `{expression}`\n"
            f"✅ **Output:** `{result}`\n\n"
            "🔭 *Calculated with 99.9% precision.*",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ **Mathematical Error**\n`{str(e)}`")

async def random_joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a random joke with Einstein flair"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything! ⚛️",
        "Why don't eggs tell jokes? They'd crack each other up! 🥚",
        "What do you call a fake noodle? An impasta! 🍝",
        "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
        "Why don't skeletons fight each other? They don't have the guts! 💀",
        "What do you call a bear with no teeth? A gummy bear! 🐻",
        "Why did the coffee file a police report? It got mugged! ☕",
        "What's orange and sounds like a parrot? A carrot! 🥕"
    ]
    
    import random
    joke = random.choice(jokes)
    reply_text = (
        "😄 **Einstein's Laboratory of Humor**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{joke}\n\n"
        "🧪 *\"Laughter is the shortest distance between two people.\"*"
    )
    await update.message.reply_text(reply_text, parse_mode='HTML')

async def random_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a random inspirational quote with Einstein flair"""
    quotes = [
        "The only way to do great work is to love what you do. - Steve Jobs 💪",
        "Innovation distinguishes between a leader and a follower. - Steve Jobs 🚀",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt ✨",
        "In the middle of difficulty lies opportunity. - Albert Einstein 💡",
        "Success is not final, failure is not fatal. - Winston Churchill 🏆"
    ]
    
    import random
    quote = random.choice(quotes)
    reply_text = (
        "📜 **Einstein's Archive of Wisdom**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{quote}\n\n"
        "✨ *Words to light up your neural pathways.*"
    )
    await update.message.reply_text(reply_text, parse_mode='HTML')

async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roll a dice"""
    import random
    
    # Check if user specified number of sides
    sides = 6
    if context.args:
        try:
            sides = int(context.args[0])
            if sides < 2 or sides > 100:
                sides = 6
        except (ValueError, IndexError):
            sides = 6
    result = random.randint(1, sides)
    
    reply_text = (
        "🎲 **Einstein's Probability Experiment**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 **SIDES:** `{sides}`\n"
        f"✨ **RESULT:** `{result}`\n\n"
        "🔭 *\"God does not play dice with the universe.\"*"
    )
    await update.message.reply_text(reply_text, parse_mode='HTML')

async def flip_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Flip a coin with Einstein flair"""
    import random
    result = random.choice(['Heads', 'Tails'])
    emoji = '🪙'
    
    reply_text = (
        "🪙 **Einstein's Quantum Toss**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Outcome:** `{result}`\n\n"
        "✨ *Every action has an equal and opposite reaction.*"
    )
    await update.message.reply_text(reply_text, parse_mode='HTML')
    await update.message.reply_text(
        f"🪙 Flipping coin...\n\n"
        f"{emoji} **{result}**!\n\n"
        f"{'👑 Heads wins!' if result == 'Heads' else '✨ Tails wins!'}",
        parse_mode='HTML'
    )

async def world_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current time in different timezones"""
    from datetime import datetime
    import pytz
    
    if not context.args:
        # Show current time in major cities
        cities = [
            ('UTC', 'UTC'),
            ('Dhaka', 'Asia/Dhaka'),
            ('New York', 'America/New_York'),
            ('London', 'Europe/London'),
            ('Tokyo', 'Asia/Tokyo'),
            ('Sydney', 'Australia/Sydney'),
            ('Dubai', 'Asia/Dubai'),
        ]
        
        msg = "🌍 **World Time**\n\n"
        for city, tz in cities:
            try:
                time = datetime.now(pytz.timezone(tz)).strftime('%Y-%m-%d %H:%M:%S')
                msg += f"📍 {city}: `{time}`\n"
            except:
                time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                msg += f"📍 {city}: `{time} UTC`\n"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        return
    
    # Try to get time for specific city
    city = " ".join(context.args)
    
    # Map common city names to timezones
    city_map = {
        'dhaka': 'Asia/Dhaka',
        'kolkata': 'Asia/Kolkata',
        'mumbai': 'Asia/Kolkata',
        'delhi': 'Asia/Kolkata',
        'new york': 'America/New_York',
        'london': 'Europe/London',
        'tokyo': 'Asia/Tokyo',
        'sydney': 'Australia/Sydney',
        'dubai': 'Asia/Dubai',
        'paris': 'Europe/Paris',
        'berlin': 'Europe/Berlin',
        'moscow': 'Europe/Moscow',
        'beijing': 'Asia/Shanghai',
        'singapore': 'Asia/Singapore',
        'los angeles': 'America/Los_Angeles',
        'chicago': 'America/Chicago',
        'toronto': 'America/Toronto',
        'vancouver': 'America/Vancouver',
        'sao paulo': 'America/Sao_Paulo',
        'cairo': 'Africa/Cairo',
        'johannesburg': 'Africa/Johannesburg',
        'bangkok': 'Asia/Bangkok',
        'jakarta': 'Asia/Jakarta',
        'seoul': 'Asia/Seoul',
        'hong kong': 'Asia/Hong_Kong',
        'istanbul': 'Europe/Istanbul',
    }
    
    tz_name = city_map.get(city.lower())
    
    if tz_name:
        try:
            time = datetime.now(pytz.timezone(tz_name)).strftime('%Y-%m-%d %H:%M:%S')
            await update.message.reply_text(
                f"🌍 **{city.title()} Time**\n\n"
                f"📅 `{time}`\n\n"
                f"🕐 Timezone: `{tz_name}`",
                parse_mode='HTML'
            )
        except:
            await update.message.reply_text(f"❌ Could not get time for {city}")
    else:
        await update.message.reply_text(
            f"❌ Unknown city: {city}\n\n"
            f"Try: Dhaka, London, New York, Tokyo, Sydney, Dubai, Paris, etc.\n"
            f"Or use /time without arguments for major cities."
        )

async def ip_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get IP address information"""
    try:
        # Get public IP
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        public_ip = response.json().get('ip', 'Unknown')
        
        # Get IP info
        info_response = requests.get(f'http://ip-api.com/json/{public_ip}', timeout=10)
        info = info_response.json()
        
        if info.get('status') == 'success':
            msg = (
                f"🌐 **Your IP Information**\n\n"
                f"📍 **IP Address:** `{public_ip}`\n"
                f"🏢 **ISP:** {info.get('isp', 'Unknown')}\n"
                f"🏛️ **Organization:** {info.get('org', 'Unknown')}\n"
                f"🌍 **Location:** {info.get('city', 'Unknown')}, {info.get('country', 'Unknown')}\n"
                f"🏳️ **Country Code:** {info.get('countryCode', 'Unknown')}\n"
                f"📍 **Region:** {info.get('regionName', 'Unknown')}\n"
                f"📮 **ZIP:** {info.get('zip', 'Unknown')}\n"
                f"🕐 **Timezone:** {info.get('timezone', 'Unknown')}\n"
                f"📡 **Lat/Lon:** {info.get('lat', 0):.4f}, {info.get('lon', 0):.4f}\n\n"
                f"⚠️ Note: VPN/Proxy may affect accuracy"
            )
        else:
            msg = f"🌐 **Your Public IP:** `{public_ip}`\n\n⚠️ Could not fetch detailed info"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch IP info: {str(e)}")

async def wikipedia_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search Wikipedia"""
    if not context.args:
        await update.message.reply_text(
            "📚 Wikipedia Search\n\n"
            "Usage: /wiki [search term]\n\n"
            "Examples:\n"
            "/wiki Albert Einstein\n"
            "/wiki Python programming\n"
            "/wiki Bangladesh"
        )
        return
    
    query = " ".join(context.args)
    
    try:
        await update.message.reply_text(f"🔍 Searching Wikipedia for: {query}...")
        
        # Wikipedia API
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query.replace(' ', '_'))}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            title = data.get('title', query)
            extract = data.get('extract', 'No information available')
            page_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')
            
            msg = (
                f"📚 **{title}**\n\n"
                f"{extract[:2000]}\n\n"
            )
            if page_url:
                msg += f"🔗 Read more: {page_url}"
            
            await update.message.reply_text(msg, parse_mode='HTML')
        else:
            # Try search API
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(query)}&format=json"
            search_response = requests.get(search_url, timeout=10)
            search_data = search_response.json()
            
            results = search_data.get('query', {}).get('search', [])
            if results:
                msg = f"📚 Wikipedia search results for '{query}':\n\n"
                for i, result in enumerate(results[:5], 1):
                    snippet = result.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', '')
                    title = result.get('title', '')
                    msg += f"{i}. **{title}**\n{snippet[:100]}...\n\n"
                await update.message.reply_text(msg, parse_mode='HTML')
            else:
                await update.message.reply_text(f"❌ No Wikipedia results found for: {query}")
                
    except Exception as e:
        await update.message.reply_text(f"❌ Wikipedia search error: {str(e)}")

async def translate_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate a replied-to message"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("❌ Please reply to a text message to translate it.")
        return

    text_to_translate = update.message.reply_to_message.text
    target_lang = " ".join(context.args) if context.args else "english"
    
    # Map language names to codes
    lang_map = {
        'english': 'en', 'spanish': 'es', 'french': 'fr', 'german': 'de',
        'italian': 'it', 'portuguese': 'pt', 'russian': 'ru',
        'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko',
        'arabic': 'ar', 'hindi': 'hi', 'bengali': 'bn', 'bangla': 'bn',
        'dutch': 'nl', 'polish': 'pl', 'turkish': 'tr',
        'vietnamese': 'vi', 'thai': 'th', 'indonesian': 'id'
    }
    
    target_code = lang_map.get(target_lang.lower(), target_lang.lower()[:2])
    
    # Correction for "bangali" typo or variations
    if 'bangali' in target_lang.lower() or 'bengali' in target_lang.lower() or 'bangla' in target_lang.lower():
        target_code = 'bn'
        target_lang = 'Bengali'
    
    try:
        # Using mymemory API (free)
        url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text_to_translate)}&langpair=autodetect|{target_code}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('responseStatus') == 200:
            translation = data.get('responseData', {}).get('translatedText', '')
            await update.message.reply_text(
                f"👨‍🔬 **Einstein Translation**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🎯 **Target:** {target_lang.title()}\n\n"
                f"{translation}",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Translation service failed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate text using free API"""
    if len(context.args) < 3:
        await update.message.reply_text(
            "🌐 Text Translation\n\n"
            "Usage: /translate [text] to [language]\n\n"
            "Examples:\n"
            "/translate Hello to Spanish\n"
            "/translate How are you to Bengali\n"
            "/translate Good morning to Hindi\n\n"
            "Supported languages:\n"
            "English, Spanish (es), French (fr), German (de),\n"
            "Italian (it), Portuguese (pt), Russian (ru),\n"
            "Chinese (zh), Japanese (ja), Korean (ko),\n"
            "Arabic (ar), Hindi (hi), Bengali (bn),\n"
            "Dutch (nl), Polish (pl), Turkish (tr),\n"
            "Vietnamese (vi), Thai (th), Indonesian (id)"
        )
        return
    
    # Find "to" in arguments
    try:
        to_index = context.args.index('to')
        text = " ".join(context.args[:to_index])
        target_lang = " ".join(context.args[to_index + 1:])
    except ValueError:
        await update.message.reply_text("❌ Usage: /translate [text] to [language]")
        return
    
    # Map language names to codes
    lang_map = {
        'english': 'en', 'spanish': 'es', 'french': 'fr', 'german': 'de',
        'italian': 'it', 'portuguese': 'pt', 'russian': 'ru',
        'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko',
        'arabic': 'ar', 'hindi': 'hi', 'bengali': 'bn', 'bangla': 'bn',
        'dutch': 'nl', 'polish': 'pl', 'turkish': 'tr',
        'vietnamese': 'vi', 'thai': 'th', 'indonesian': 'id',
        'greek': 'el', 'czech': 'cs', 'romanian': 'ro',
        'swedish': 'sv', 'norwegian': 'no', 'danish': 'da',
        'finnish': 'fi', 'hebrew': 'he', 'urdu': 'ur',
        'tamil': 'ta', 'telugu': 'te', 'marathi': 'mr',
        'malayalam': 'ml', 'punjabi': 'pa', 'gujarati': 'gu'
    }
    
    # Get language code
    target_code = lang_map.get(target_lang.lower())
    if not target_code:
        target_code = target_lang.lower()[:2]  # Assume it's already a code
    
    try:
        await update.message.reply_text(f"🌐 Translating to {target_lang.title()}...")
        
        # Using mymemory API (free)
        url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text)}&langpair=en|{target_code}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('responseStatus') == 200:
            translation = data.get('responseData', {}).get('translatedText', '')
            
            await update.message.reply_text(
                f"🌐 **Translation**\n\n"
                f"🇬🇧 **Original:** {text}\n\n"
                f"🎯 **Translated ({target_lang.title()}):**\n"
                f"{translation}",
                parse_mode='HTML'
            )
        else:
            # Fallback to alternative translation method
            await update.message.reply_text(
                f"⚠️ Translation service unavailable\n\n"
                f"Original: {text}\n"
                f"Target language: {target_lang}"
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Translation error: {str(e)}")

async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a timer/reminder"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "⏰ Timer & Reminder\n\n"
            "Usage: /timer [time] [message]\n\n"
            "Examples:\n"
            "/timer 5m Take a break\n"
            "/timer 1h Meeting with team\n"
            "/timer 30s Test notification\n"
            "/timer 2h 30m Dinner time\n\n"
            "Time format:\n"
            "• s = seconds\n"
            "• m = minutes\n"
            "• h = hours"
        )
        return
    
    # Parse time
    time_arg = context.args[0]
    message = " ".join(context.args[1:])
    
    # Calculate seconds
    total_seconds = 0
    try:
        import re
        # Match patterns like 1h30m, 5m, 2h, etc.
        hours = re.search(r'(\d+)h', time_arg)
        minutes = re.search(r'(\d+)m', time_arg)
        seconds = re.search(r'(\d+)s', time_arg)
        
        if hours:
            total_seconds += int(hours.group(1)) * 3600
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))
        
        # If no unit specified, assume minutes
        if total_seconds == 0:
            total_seconds = int(time_arg) * 60
            
    except:
        await update.message.reply_text("❌ Invalid time format. Use: 5m, 1h, 30s, 2h30m")
        return
    
    if total_seconds <= 0 or total_seconds > 86400:  # Max 24 hours
        await update.message.reply_text("❌ Invalid time. Range: 1 second to 24 hours")
        return
    
    # Confirm timer set
    time_str = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m {total_seconds % 60}s"
    await update.message.reply_text(
        f"⏰ **Timer Set!**\n\n"
        f"Message: {message}\n"
        f"Duration: {time_str}\n\n"
        f"I'll remind you when time is up!",
        parse_mode='HTML'
    )
    
    # Start timer in background
    import asyncio
    await asyncio.sleep(total_seconds)
    
    # Send reminder
    await update.message.reply_text(
        f"⏰ **TIME'S UP!**\n\n"
        f"🔔 Reminder: {message}\n\n"
        f"✅ Timer completed!",
        parse_mode='HTML'
    )

async def unit_converter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convert between units"""
    if len(context.args) < 4:
        await update.message.reply_text(
            "📐 Unit Converter\n\n"
            "Usage: /convert [value] [unit] to [unit]\n\n"
            "Examples:\n"
            "/convert 100 km to miles\n"
            "/convert 25 celsius to fahrenheit\n"
            "/convert 1 kg to lbs\n"
            "/convert 5 feet to meters\n"
            "/convert 1 gb to mb\n\n"
            "Categories:\n"
            "• Length: km, miles, meters, feet, inches\n"
            "• Weight: kg, lbs, grams, ounces\n"
            "• Temperature: celsius, fahrenheit, kelvin\n"
            "• Digital: gb, mb, kb, tb\n"
            "• Area: sqkm, sqmiles, acres"
        )
        return
    
    try:
        value = float(context.args[0])
        from_unit = context.args[1].lower()
        to_unit = context.args[3].lower()
        
        # Conversion factors
        conversions = {
            # Length
            ('km', 'miles'): 0.621371,
            ('miles', 'km'): 1.60934,
            ('meters', 'feet'): 3.28084,
            ('feet', 'meters'): 0.3048,
            ('meters', 'inches'): 39.3701,
            ('inches', 'meters'): 0.0254,
            ('km', 'meters'): 1000,
            ('meters', 'km'): 0.001,
            
            # Weight
            ('kg', 'lbs'): 2.20462,
            ('lbs', 'kg'): 0.453592,
            ('kg', 'grams'): 1000,
            ('grams', 'kg'): 0.001,
            ('ounces', 'grams'): 28.3495,
            ('grams', 'ounces'): 0.035274,
            
            # Digital
            ('gb', 'mb'): 1024,
            ('mb', 'gb'): 1/1024,
            ('tb', 'gb'): 1024,
            ('gb', 'tb'): 1/1024,
            ('mb', 'kb'): 1024,
            ('kb', 'mb'): 1/1024,
            
            # Area
            ('sqkm', 'sqmiles'): 0.386102,
            ('sqmiles', 'sqkm'): 2.58999,
            ('acres', 'sqmeters'): 4046.86,
            ('sqmeters', 'acres'): 0.000247105,
        }
        
        result = None
        
        # Check for direct conversion
        if (from_unit, to_unit) in conversions:
            result = value * conversions[(from_unit, to_unit)]
        
        # Temperature conversions
        elif from_unit in ['celsius', 'c'] and to_unit in ['fahrenheit', 'f']:
            result = (value * 9/5) + 32
        elif from_unit in ['fahrenheit', 'f'] and to_unit in ['celsius', 'c']:
            result = (value - 32) * 5/9
        elif from_unit in ['celsius', 'c'] and to_unit in ['kelvin', 'k']:
            result = value + 273.15
        elif from_unit in ['kelvin', 'k'] and to_unit in ['celsius', 'c']:
            result = value - 273.15
        elif from_unit in ['fahrenheit', 'f'] and to_unit in ['kelvin', 'k']:
            result = (value - 32) * 5/9 + 273.15
        elif from_unit in ['kelvin', 'k'] and to_unit in ['fahrenheit', 'f']:
            result = (value - 273.15) * 9/5 + 32
        
        if result is not None:
            await update.message.reply_text(
                f"📐 **Unit Conversion**\n\n"
                f"{value} {from_unit} = **{result:.4f}** {to_unit}",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ Conversion not available: {from_unit} to {to_unit}\n\n"
                f"Use /convert for available units"
            )
            
    except ValueError:
        await update.message.reply_text("❌ Invalid value. Please enter a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Conversion error: {str(e)}")

async def random_facts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get random interesting facts"""
    facts = [
        "🐙 Octopuses have three hearts, blue blood, and nine brains!",
        "🍯 Honey never spoils. Archaeologists have found 3000-year-old honey in ancient Egyptian tombs!",
        "🦒 A giraffe's tongue is so long it can clean its own ears!",
        "🦘 Kangaroos can't walk backward!",
        "🐌 A snail can sleep for three years at a time!",
        "🦈 Sharks are the only fish that can blink with both eyes!",
        "🦉 An owl can turn its head 270 degrees but can't move its eyes!",
        "🐘 Elephants are the only mammals that can't jump!",
        "🦛 A hippopotamus can run faster than a human!",
        "🐧 Penguins can drink salt water because they have special glands!",
        "🦋 Butterflies taste with their feet!",
        "🦀 A group of flamingos is called a 'flamboyance'!",
        "🦚 Peacocks can fly, despite their massive tails!",
        "🦜 Parrots can live for over 80 years!",
        "🐯 Tigers have striped skin, not just striped fur!",
        "🦓 Every zebra has a unique pattern of stripes, like human fingerprints!",
        "🦍 Gorillas can catch human colds and other illnesses!",
        "🐨 Koalas sleep up to 22 hours a day!",
        "🦥 Sloths can hold their breath longer than dolphins!",
        "🦔 A hedgehog's heart beats 300 times per minute!"
    ]
    
    import random
    fact = random.choice(facts)
    await update.message.reply_text(f"🤓 **Did You Know?**\n\n{fact}", parse_mode='HTML')

async def text_formatter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format text (uppercase, lowercase, reverse, etc.)"""
    if not context.args:
        await update.message.reply_text(
            "📝 Text Formatter\n\n"
            "Usage: /format [style] [text]\n\n"
            "Styles:\n"
            "• upper - UPPERCASE\n"
            "• lower - lowercase\n"
            "• title - Title Case\n"
            "• reverse - esreveR\n"
            "• bold - *Bold Text*\n"
            "• italic - _Italic Text_\n"
            "• code - `Code Format`\n"
            "• spoiler - ||Spoiler||\n\n"
            "Examples:\n"
            "/format upper hello world\n"
            "/format reverse hello"
        )
        return
    
    style = context.args[0].lower()
    text = " ".join(context.args[1:])
    
    if not text:
        await update.message.reply_text("❌ Please provide text to format")
        return
    
    formatted = text
    
    if style == 'upper':
        formatted = text.upper()
    elif style == 'lower':
        formatted = text.lower()
    elif style == 'title':
        formatted = text.title()
    elif style == 'reverse':
        formatted = text[::-1]
    elif style == 'bold':
        formatted = f"*{text}*"
    elif style == 'italic':
        formatted = f"_{text}_"
    elif style == 'code':
        formatted = f"`{text}`"
    elif style == 'spoiler':
        formatted = f"||{text}||"
    else:
        await update.message.reply_text(f"❌ Unknown style: {style}\nUse /format for available styles")
        return
    
    await update.message.reply_text(
        f"📝 **Text Formatter**\n\n"
        f"Style: {style.title()}\n"
        f"Result:\n{formatted}",
        parse_mode='HTML'
    )

async def music_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search and play/download music from YouTube as audio"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    if not context.args:
        await update.message.reply_text(
            "🎵 **Music Player & Search**\n"
            "━━━━━━━━━━━━━━━\n"
            "Search and play any song directly!\n\n"
            "**Usage:**\n"
            "/play [song name] - Search and play\n"
            "/music [url] - Download from link\n\n"
            "**Example:**\n"
            "/play Atif Aslam songs\n"
            "/play Believer Imagine Dragons",
            parse_mode='HTML'
        )
        return

    query = " ".join(context.args)
    download_dir = "d:/clow bot/downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    progress_msg = await update.message.reply_text("🔍 `Searching for your music...`", parse_mode='HTML')

    try:
        import yt_dlp
        
        # Audio specific options - download native m4a/webm audio without ffmpeg
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [],  # No ffmpeg postprocessing
            'default_search': 'ytsearch1',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await progress_msg.edit_text("⚡ `Downloading audio...`", parse_mode='HTML')
            info = ydl.extract_info(query if query.startswith('http') else f"ytsearch1:{query}", download=True)
            
            # If it's a search, get the first entry
            if 'entries' in info:
                video_info = info['entries'][0]
            else:
                video_info = info
                
            title = video_info.get('title', 'Unknown Title')
            filename = ydl.prepare_filename(video_info)
            # No postprocessing, keep original extension (m4a/webm)

            if os.path.exists(filename):
                await progress_msg.edit_text(f"☁️ `Uploading: {title[:40]}...` 📤", parse_mode='HTML')
                
                with open(filename, 'rb') as audio_file:
                    await update.message.reply_audio(
                        audio=audio_file,
                        title=title,
                        performer="👨‍🔬 OpenClowd Einstein",
                        caption=f"🎵 **{title}**\n\n✨ *Enjoy your high-quality music!*",
                        parse_mode='HTML'
                    )
                
                os.remove(filename)
                await progress_msg.delete()
            else:
                await progress_msg.edit_text("❌ Music file not found after download.")
                
    except Exception as e:
        await progress_msg.edit_text(f"❌ Music error: {str(e)[:200]}")

# Video Tasks Persistence
TASKS_FILE = "d:/clow bot/pending_tasks.json"

def save_pending_task(chat_id, user_id, command, url, is_hq=False):
    try:
        tasks = []
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r') as f:
                tasks = json.load(f)
        
        task_id = f"{chat_id}_{int(asyncio.get_event_loop().time())}"
        tasks.append({
            'id': task_id,
            'chat_id': chat_id,
            'user_id': user_id,
            'command': command,
            'url': url,
            'is_hq': is_hq,
            'timestamp': datetime.now().isoformat()
        })
        
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=4)
        return task_id
    except Exception as e:
        print(f"Error saving task: {e}")
        return None

def remove_pending_task(task_id):
    try:
        if not os.path.exists(TASKS_FILE):
            return
        
        with open(TASKS_FILE, 'r') as f:
            tasks = json.load(f)
        
        tasks = [t for t in tasks if t['id'] != task_id]
        
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=4)
    except Exception as e:
        print(f"Error removing task: {e}")

async def continue_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume all uncompleted tasks from the pending_tasks.json file"""
    if str(update.effective_user.id) != str(ALLOWED_USER_ID):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not os.path.exists(TASKS_FILE):
        await update.message.reply_text("✅ No pending tasks found.")
        return

    try:
        with open(TASKS_FILE, 'r') as f:
            tasks = json.load(f)
        
        if not tasks:
            await update.message.reply_text("✅ No pending tasks to resume.")
            return

        await update.message.reply_text(f"🔄 Resuming **{len(tasks)}** pending tasks... ⏳", parse_mode='HTML')
        
        for task in tasks:
            # Create a mock update/context to re-run the downloader
            # This is a bit tricky with python-telegram-bot, better to call a modified downloader or just pass data
            context.args = [task['url']]
            # We need to manually handle the HQ flag since it's usually based on the command name
            # A cleaner way is to call the video_downloader logic directly
            asyncio.create_task(process_resumed_task(update, context, task))
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error resuming tasks: {e}")

async def process_resumed_task(update, context, task):
    """Helper to process a single resumed task"""
    # Create a wrapper or call downloader logic with task data
    # For now, let's just use the existing downloader by modifying context
    try:
        # We need the original chat/user info which we stored
        # But we use the current update for replying
        await video_downloader(update, context, resumed_task=task)
    except Exception as e:
        print(f"Error in resumed task {task['id']}: {e}")

def split_file(file_path, chunk_size_mb=1900):
    """Splits a file into chunks of specified size (default 1.9GB for Telegram)"""
    file_size = os.path.getsize(file_path)
    chunk_size = chunk_size_mb * 1024 * 1024
    num_chunks = math.ceil(file_size / chunk_size)
    
    chunks = []
    base_name = os.path.basename(file_path)
    output_dir = os.path.dirname(file_path)
    
    with open(file_path, 'rb') as f:
        for i in range(num_chunks):
            chunk_filename = f"{base_name}.part{i+1:03}"
            chunk_path = os.path.join(output_dir, chunk_filename)
            with open(chunk_path, 'wb') as chunk_f:
                chunk_f.write(f.read(chunk_size))
            chunks.append(chunk_path)
            
    return chunks

async def send_large_file(update, context, file_path, caption):
    """Sends a file, splitting it if it exceeds Telegram's size limit"""
    MAX_SIZE_MB = 1900 # Stay safe under 2GB limit
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size_mb <= MAX_SIZE_MB:
        with open(file_path, 'rb') as f:
            try:
                if file_path.lower().endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi')):
                    await update.message.reply_video(
                        video=f, 
                        caption=caption,
                        supports_streaming=True, 
                        read_timeout=1200, 
                        write_timeout=1200,
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_document(
                        document=f, 
                        caption=caption,
                        read_timeout=1200, 
                        write_timeout=1200,
                        parse_mode='HTML'
                    )
                return True
            except Exception as e:
                print(f"Error sending file normally: {e}")
                f.seek(0)
                await update.message.reply_document(
                    document=f, 
                    caption=caption,
                    read_timeout=1200, 
                    write_timeout=1200,
                    parse_mode='HTML'
                )
                return True
    else:
        # File is too large, need to split
        await update.message.reply_text(f"📦 <b>File is large ({file_size_mb/1024:.2f} GB).</b>\nEinstein is splitting it into parts for you...", parse_mode='HTML')
        chunks = split_file(file_path, MAX_SIZE_MB)
        
        for i, chunk in enumerate(chunks):
            part_caption = f"{caption}\n\n📦 <b>Part {i+1} of {len(chunks)}</b>"
            with open(chunk, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    caption=part_caption,
                    read_timeout=1200,
                    write_timeout=1200,
                    parse_mode='HTML'
                )
            os.remove(chunk) # Clean up chunk after sending
        return True

async def video_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, resumed_task=None):
    """Universal video downloader - Strictly single video focus with professional handling"""
    if not await check_auth(update): return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
    
    if resumed_task:
        url = resumed_task.get('url')
        is_hq = resumed_task.get('is_hq', False)
        task_id = resumed_task.get('id')
    else:
        if not context.args:
            await update.message.reply_text("📹 **Einstein Universal Video Downloader**\n━━━━━━━━━━━━━━━━━━━━━\nSend me any video URL and I will download it for you.\n\n✨ *Only the exact video linked will be processed.*", parse_mode='HTML')
            return
        url = context.args[0]
        is_hq = False
        if update.message and update.message.text:
            is_hq = any(x in update.message.text.lower() for x in ['/video_hq', '4k', '8k'])
        task_id = save_pending_task(update.effective_chat.id, update.effective_user.id, "/video", url, is_hq)

    if not url or not url.startswith(('http://', 'https://')):
        if not resumed_task: await update.message.reply_text("❌ Please provide a valid URL.")
        return

    download_dir = "d:/clow bot/downloads"
    os.makedirs(download_dir, exist_ok=True)
    task_subdir = os.path.join(download_dir, str(uuid.uuid4())[:8])
    os.makedirs(task_subdir, exist_ok=True)
    
    try:
        # Animated status update for better UX
        status_msg = await update.message.reply_text("🧬 `Einstein System: Initializing media extraction...` 🧠", parse_mode='HTML')
        
        animations = [
            "📡 `Connecting to server...` ⚛️",
            "🔍 `Analyzing metadata...` 🔬",
            "⚡ `Optimizing download path...` 🚀"
        ]
        
        for anim in animations:
            try:
                await status_msg.edit_text(anim, parse_mode='HTML')
                await asyncio.sleep(0.5)
            except: pass
        
        # Professional yt-dlp options enforcing single video with ultra-fast speed optimization
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{task_subdir}/%(id)s_%(timestamp)s.%(ext)s',
            'noplaylist': True,
            'playlist_items': '1',
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': None,
            'nothreads': 16,
            'buffersize': 1024 * 1024,
            'http_chunk_size': 1024 * 1024,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android'],
                    'player_skip': ['webpage', 'configs', 'js'],
                },
                'tiktok': {
                    'app_version': '20.1.1',
                    'manifest_app_name': 'aweme',
                }
            }
        }
        
        # Site-specific optimizations
        if 'faphouse.com' in url:
            print("🎯 FapHouse detected - finding the main video...")
            ydl_opts_analysis = {'quiet': True, 'extract_flat': 'in_playlist', 'playlistend': 50}
            with yt_dlp.YoutubeDL(ydl_opts_analysis) as ydl_analysis:
                try:
                    playlist_info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl_analysis.extract_info(url, download=False))
                    if playlist_info and 'entries' in playlist_info:
                        entries = [e for e in playlist_info['entries'] if e]
                        if entries:
                            valid_entries = []
                            for entry in entries:
                                title_lower = (entry.get('title') or '').lower()
                                url_lower = (entry.get('url') or '').lower()
                                if any(k in title_lower or k in url_lower for k in ['preview', 'heatmap', 'trailer']):
                                    continue
                                valid_entries.append(entry)
                            if valid_entries:
                                valid_entries.sort(key=lambda x: x.get('duration', 0) or 0, reverse=True)
                                url = valid_entries[0].get('url', url)
                                print(f"🎬 Selected main video: {url}")
                except Exception as analysis_err:
                    print(f"⚠️ Analysis error: {analysis_err}")
        
        # Terabox Mirror Transformation
        terabox_mirrors = ['teraboxshare.com', '1024tera.com', 'nephobox.com', '4funbox.com', 'mirrobox.com', 'momotera.com', 'teraboxapp.com', 'terabox.app', 'tibabox.com', 'freeterabox.com', '1024terabox.com']
        if any(m in url for m in terabox_mirrors) or 'terabox.com' in url:
            ydl_opts['headers']['Referer'] = 'https://www.terabox.com/'
            for m in terabox_mirrors:
                if m in url: 
                    url = url.replace(m, 'terabox.com')
                    break

        await status_msg.edit_text("📥 `Downloading from source...` ✨", parse_mode='HTML')

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            except Exception:
                # Ultimate fallback for compatibility
                ydl_opts['format'] = 'best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_fallback:
                    info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl_fallback.extract_info(url, download=True))
            
            filename = ydl.prepare_filename(info) if info else None
            
            # Enhanced fallback logic to find the file
            if not filename or not os.path.exists(filename):
                if os.path.exists(task_subdir):
                    files = os.listdir(task_subdir)
                    if files:
                        # Pick the largest file in the task directory as the most likely candidate
                        full_paths = [os.path.join(task_subdir, f) for f in files]
                        filename = max(full_paths, key=os.path.getsize)
                        print(f"🧩 Fallback found file: {filename}")
            
            if filename and os.path.exists(filename):
                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                await status_msg.edit_text(f"✅ <b>Downloaded!</b> ({file_size_mb:.2f} MB)\n📤 <b>Uploading to Telegram...</b>", parse_mode='HTML')
                
                title = info.get('title', 'Video')
                # Use robust HTML escaping for title
                safe_title = escape_html(title)
                caption = f"🎬 <b>{safe_title[:100]}</b>\n━━━━━━━━━━━━━━━━━━━━━\n👨‍🔬 <i>Einstein Optimization Active</i>\n📥 @alberteinstein247_bot"
                
                # Use send_large_file to handle files of any size (up to 30GB+)
                await send_large_file(update, context, filename, caption)
                
                if task_id: remove_pending_task(task_id)
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ <b>Einstein Error:</b> Media not found after processing.", parse_mode='HTML')
                
    except Exception as e:
        if task_id: remove_pending_task(task_id)
        import traceback
        error_detail = traceback.format_exc()
        print(f"Downloader Error Detail:\n{error_detail}")
        error_str = str(e)
        if "ReadError" in error_str or "timeout" in error_str.lower():
            friendly_error = "📡 Network connection unstable. Einstein is retrying..."
        else:
            friendly_error = f"Download failed: {escape_html(error_str[:100])}"
            
        if 'status_msg' in locals(): 
            await status_msg.edit_text(f"❌ <b>{friendly_error}</b>", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ <b>{friendly_error}</b>", parse_mode='HTML')
    finally:
        if os.path.exists(task_subdir): shutil.rmtree(task_subdir)
async def universal_file_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Downloads any file type (jpg, png, doc, xlsx, etc.) from a direct link with animation"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    
    download_dir = "d:/clow bot/downloads"
    os.makedirs(download_dir, exist_ok=True)
    task_subdir = os.path.join(download_dir, str(uuid.uuid4())[:8])
    os.makedirs(task_subdir, exist_ok=True)
    
    status_msg = await update.message.reply_text("🧬 `Einstein System: Initializing secure file transfer...` 🧠", parse_mode='HTML')
    
    try:
        animations = [
            "📡 `Establishing uplink...` ⚛️",
            "🛡️ `Verifying data integrity...` 🔬",
            "📥 `Acquiring packet fragments...` ✨"
        ]
        
        for anim in animations:
            try:
                await status_msg.edit_text(anim, parse_mode='HTML')
                await asyncio.sleep(0.5)
            except: pass

        # Use requests to download the file with high-speed chunking and retries
        session = requests.Session()
        retries = requests.adapters.Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        response = session.get(url, stream=True, timeout=(10, 300), headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        })
        response.raise_for_status()
        
        # Try to get filename from headers or URL
        filename = ""
        if "Content-Disposition" in response.headers:
            cd = response.headers.get("Content-Disposition")
            if "filename=" in cd:
                filename = cd.split("filename=")[1].strip('"\'')
        
        if not filename:
            filename = url.split('/')[-1].split('?')[0]
            if not filename or '.' not in filename:
                filename = f"file_{str(uuid.uuid4())[:8]}"
        
        # Ensure safe filename
        filename = "".join([c for c in filename if c.isalnum() or c in ('.', '_', '-')]).strip()
        file_path = os.path.join(task_subdir, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024): # 1MB chunks for speed
                if chunk:
                    f.write(chunk)
        
        if os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            await status_msg.edit_text(f"✅ <b>Transfer Complete!</b> ({file_size_mb:.2f} MB)\n📤 <b>Uploading to Terminal...</b>", parse_mode='HTML')
            
            # Use robust HTML escaping for filename
            safe_filename = escape_html(filename)
            caption = f"📄 <b>File:</b> <code>{safe_filename}</code>\n━━━━━━━━━━━━━━━━━━━━━\n👨‍🔬 <i>Einstein Optimization Active</i>\n📥 @alberteinstein247_bot"
            
            # Use send_large_file to handle files of any size
            await send_large_file(update, context, file_path, caption)
            
            await status_msg.delete()
        else:
            await status_msg.edit_text("<b>❌ Einstein Error:</b> File vanished during transfer.", parse_mode='HTML')
            
    except Exception as e:
        print(f"Universal Downloader Error: {e}")
        await status_msg.edit_text(f"<b>❌ Transfer Failed:</b> {escape_html(str(e)[:100])}", parse_mode='HTML')
    finally:
        if os.path.exists(task_subdir):
            shutil.rmtree(task_subdir)

async def play_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Play video directly without downloading - instant streaming"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
    
    if not context.args:
        await update.message.reply_text(
            "▶️ **Instant Video Player**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Play videos directly from ANY platform without downloading!\n\n"
            "**📺 Social Media:**\n"
            "YouTube, Facebook, Instagram Reels/Stories, TikTok (No Watermark)\n"
            "Twitter/X, Reddit, Pinterest, LinkedIn\n\n"
            "**🎬 Video Sites:**\n"
            "Vimeo, Dailymotion, Twitch, SoundCloud, Rumble\n\n"
            "**☁️ Cloud Storage:**\n"
            "Terabox, Diskwala, Mega.nz, MediaFire, Google Drive\n"
            "Dropbox, Box, OneDrive\n\n"
            "**📦 File Sharing:**\n"
            "Zippyshare, Racaty, KrakenFiles, WeTransfer, File.io\n\n"
            "**🔞 Adult Sites:**\n"
            "Pornhub, Xvideos, Xhamster, FapHouse, SpankBang, RedTube, YouPorn, etc.\n\n"
            "**💾 Direct Links:**\n"
            "MP4, WebM, MKV, MOV, AVI - Any direct video URL\n\n"
            "**🚀 Usage:**\n"
            "• `/play [URL]` - Stream video instantly (no download)\n"
            "• `/stream [URL]` - Same as /play\n\n"
            "**Examples:**\n"
            "• `/play https://youtube.com/watch?v=...`\n"
            "• `/play https://pornhub.com/...`\n"
            "• `/play https://terabox.com/...`\n"
            "• `/play https://tiktok.com/...`\n"
            "• `/play https://instagram.com/reel/...`\n\n"
            "⚡ *Instant streaming - no wait time!*\n"
            "✨ *\"Simplicity is the ultimate sophistication.\"*",
            parse_mode='HTML'
        )
        return
    
    url = context.args[0]
    
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Please provide a valid URL starting with http:// or https://")
        return
    
    progress_msg = await update.message.reply_text("⏳ `Extracting video for streaming...` 🎬", parse_mode='HTML')
    
    try:
        # Extract direct video URL using yt-dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,  # Don't download, just extract URL
            'force_generic_extractor': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                await progress_msg.edit_text("❌ Could not extract video information.")
                return
            
            # Get video details
            title = info.get('title', 'Video')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail', None)
            
            # Get the best video URL
            video_url = None
            if 'url' in info:
                video_url = info['url']
            elif 'formats' in info and len(info['formats']) > 0:
                # Find best MP4 format
                mp4_formats = [f for f in info['formats'] if f.get('ext') == 'mp4']
                if mp4_formats:
                    # Sort by quality (height), prefer 720p for streaming
                    mp4_formats.sort(key=lambda x: abs(x.get('height', 0) - 720))
                    video_url = mp4_formats[0].get('url')
                else:
                    # Get best available format
                    video_url = info['formats'][-1].get('url')
            
            if not video_url:
                await progress_msg.edit_text("❌ Could not extract video stream URL.\n\nTry `/video [URL]` to download instead.")
                return
            
            await progress_msg.edit_text(f"▶️ `Streaming:` **{title[:50]}** 🎬", parse_mode='HTML')
            
            # Send video for streaming
            try:
                await update.message.reply_video(
                    video=video_url,  # Direct streaming URL
                    caption=(
                        f"🎬 **{title[:100]}**\n"
                        f"⏱️ Duration: `{duration//60}:{duration%60:02d}`\n\n"
                        f"⚡ *Instant Stream - No Download Required*\n"
                        f"📥 @alberteinstein247_bot"
                    ),
                    supports_streaming=True,
                    parse_mode='HTML',
                    read_timeout=300,  # Increased timeout for large files
                    write_timeout=300,
                    connect_timeout=300,
                    pool_timeout=300
                )
                await progress_msg.delete()
                
            except Exception as stream_error:
                print(f"Stream error: {stream_error}")
                # If streaming fails (like Entity Too Large), suggest downloading
                if "Request Entity Too Large" in str(stream_error) or "413" in str(stream_error):
                    await progress_msg.edit_text(
                        f"⚠️ **File Too Large for Direct Stream**\n\n"
                        f"Telegram limits direct URL streaming for very large files.\n"
                        f"Try downloading it instead:\n"
                        f"`/video {url}`",
                        parse_mode='HTML'
                    )
                else:
                    await progress_msg.edit_text(
                        f"⚠️ **Stream Error**\n\n"
                        f"Direct streaming failed. Try downloading instead:\n"
                        f"`/video {url}`",
                        parse_mode='HTML'
                    )
                
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Unsupported URL" in error_msg:
            await progress_msg.edit_text(
                "❌ **Unsupported URL**\n\n"
                "This platform is not supported for streaming.\n\n"
                "Try `/video [URL]` to download instead."
            )
        else:
            await progress_msg.edit_text(f"❌ Error: {error_msg[:200]}\n\nTry `/video [URL]` to download.")
    except Exception as e:
        print(f"Play error: {e}")
        await progress_msg.edit_text(f"❌ Error: {str(e)[:200]}\n\nTry `/video [URL]` to download instead.")

async def utilities_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Utility tools - QR, password, short URL, etc."""
    if not context.args:
        await update.message.reply_text(
            "🛠️ Utilities\n\n"
            "Commands:\n"
            "/utils qr [text] - Generate QR code\n"
            "/utils password [length] - Generate password\n"
            "/utils short [url] - Shorten URL\n"
            "/utils news - Latest news\n"
            "/utils joke - Random joke\n"
            "/utils quote - Random quote\n"
            "/utils fact - Random fact\n"
            "/utils dice [sides] - Roll dice\n"
            "/utils coin - Flip coin"
        )
        return
    
    action = context.args[0].lower()
    
    try:
        if action == "qr" and len(context.args) >= 2:
            text = " ".join(context.args[1:])
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            qr_path = f"d:/clow bot/qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img.save(qr_path)
            
            await update.message.reply_photo(open(qr_path, 'rb'), caption=f"📱 QR Code for: {text[:50]}")
            os.remove(qr_path)
            
        elif action == "password":
            import random
            import string
            length = int(context.args[1]) if len(context.args) > 1 else 12
            password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=length))
            await update.message.reply_text(f"🔐 Generated Password:\n`{password}`", parse_mode='HTML')
            
        elif action == "short" and len(context.args) >= 2:
            url = context.args[1]
            # Using TinyURL API
            short_url = requests.get(f"http://tinyurl.com/api-create.php?url={url}").text
            await update.message.reply_text(f"🔗 Short URL:\n{short_url}")
            
        elif action == "news":
            # Using NewsAPI or RSS
            await update.message.reply_text(
                "📰 Latest News:\n\n"
                "1. Tech: AI breakthrough in 2026\n"
                "2. World: Global climate summit\n"
                "3. Sports: Champions League updates\n\n"
                "⚠️ Add NEWS_API_KEY for real news"
            )
            
        elif action == "joke":
            await random_joke(update, context)
            
        elif action == "quote":
            await random_quote(update, context)
            
        elif action == "fact":
            await random_facts(update, context)
            
        elif action == "dice":
            await roll_dice(update, context)
            
        elif action == "coin":
            await flip_coin(update, context)
            
        elif action == "translate" and len(context.args) >= 4:
            # Simple demo translation
            text = " ".join(context.args[1:-2])
            target_lang = context.args[-1]
            await update.message.reply_text(
                f"🌐 Translation Demo\n\n"
                f"Original: {text}\n"
                f"Target: {target_lang}\n\n"
                f"⚠️ Use /translate command for full translation"
            )
            
        else:
            await update.message.reply_text("🛠️ Use /utils for available commands")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Utility error: {str(e)}")

async def discord_webhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send message to all Discord channels by default, or specific if provided"""
    if not context.args and not os.getenv("DISCORD_WEBHOOK_URL"):
        await update.message.reply_text(
            "🧪 **Einstein Discord Bridge**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Usage:\n"
            "• `/discord [message]` (sends to ALL channels in .env)\n"
            "• `/discord [webhook_url] [message]` (specific channel)\n\n"
            "👨‍🔬 *\"Everything is energy and that's all there is to it.\"*",
            parse_mode='HTML'
        )
        return
    
    try:
        webhooks_str = os.getenv("DISCORD_WEBHOOK_URL")
        
        # Determine if we are sending to all or a specific URL
        if context.args and context.args[0].startswith("http"):
            webhook_urls = [context.args[0]]
            message = " ".join(context.args[1:])
        elif webhooks_str:
            webhook_urls = [url.strip() for url in webhooks_str.split(',') if url.strip()]
            message = " ".join(context.args)
        else:
            await update.message.reply_text("❌ No webhook URLs found.")
            return

        if not message:
            await update.message.reply_text("❌ Please provide a message to transmit.")
            return
        
        success_count = 0
        total_count = len(webhook_urls)
        
        for url in webhook_urls:
            data = {
                "content": message,
                "username": "Einstein System",
                "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/d/d3/Albert_Einstein_Head.jpg"
            }
            resp = requests.post(url, json=data)
            if resp.status_code == 204:
                success_count += 1
        
        if total_count > 1:
            await update.message.reply_text(f"✅ **Transmission Complete:** Sent to `{success_count}/{total_count}` channels.", parse_mode='HTML')
        elif success_count == 1:
            await update.message.reply_text("✅ **Frequency Matched:** Message sent to Discord.", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Failed to send message to Discord.")

    except Exception as e:
        await update.message.reply_text(f"❌ Discord error: {str(e)}")

async def slack_webhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send message to Slack via webhook"""
    if not context.args:
        await update.message.reply_text(
            "💼 Slack Webhook\n\n"
            "Usage:\n"
            "/slack [webhook_url] [message]\n\n"
            "Or add SLACK_WEBHOOK_URL to .env"
        )
        return
    
    try:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL") or context.args[0]
        message = " ".join(context.args[1:]) if os.getenv("SLACK_WEBHOOK_URL") else " ".join(context.args[1:])
        
        if not message:
            await update.message.reply_text("❌ Please provide a message")
            return
        
        data = {"text": message, "username": "OpenClowd Bot"}
        response = requests.post(webhook_url, json=data)
        
        if response.status_code == 200:
            await update.message.reply_text("✅ Message sent to Slack")
        else:
            await update.message.reply_text(f"❌ Failed to send: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Slack error: {str(e)}")

# ============== CALENDAR & TRAVEL FEATURES ==============

async def calendar_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Google Calendar management - OpenClaw feature"""
    calendar_file = "d:/clow bot/calendar.json"
    
    if not context.args:
        await update.message.reply_text(
            "📅 Calendar Manager\n\n"
            "Commands:\n"
            "/calendar add '[title]' [YYYY-MM-DD] [HH:MM] - Add event\n"
            "/calendar today - Today's events\n"
            "/calendar week - This week's events\n"
            "/calendar list - All events\n"
            "/calendar delete [id] - Delete event\n\n"
            "Example: /calendar add 'Meeting' 2026-02-20 14:30"
        )
        return
    
    action = context.args[0].lower()
    
    try:
        # Load calendar
        if os.path.exists(calendar_file):
            with open(calendar_file, 'r', encoding='utf-8') as f:
                events = json.load(f)
        else:
            events = []
        
        if action == "add" and len(context.args) >= 4:
            # Parse: /calendar add "Title" 2026-02-20 14:30
            # Find title in quotes
            full_text = " ".join(context.args[1:])
            if '"' in full_text:
                parts = full_text.split('"')
                title = parts[1]
                remaining = parts[2].strip().split()
                date = remaining[0] if len(remaining) > 0 else datetime.now().strftime('%Y-%m-%d')
                time = remaining[1] if len(remaining) > 1 else "09:00"
            else:
                title = context.args[1]
                date = context.args[2] if len(context.args) > 2 else datetime.now().strftime('%Y-%m-%d')
                time = context.args[3] if len(context.args) > 3 else "09:00"
            
            event = {
                "id": len(events) + 1,
                "title": title,
                "date": date,
                "time": time,
                "created": datetime.now().isoformat()
            }
            events.append(event)
            
            with open(calendar_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            
            await update.message.reply_text(f"✅ Event added:\n📅 {title}\n📆 {date} at {time}")
            
        elif action == "today":
            today = datetime.now().strftime('%Y-%m-%d')
            today_events = [e for e in events if e['date'] == today]
            
            if today_events:
                msg = f"📅 Today's Events ({today}):\n\n"
                for e in today_events:
                    msg += f"⏰ {e['time']} - {e['title']}\n"
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text(f"📅 No events for today ({today})")
                
        elif action == "week":
            # Show next 7 days
            from datetime import timedelta
            today = datetime.now()
            week_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
            week_events = [e for e in events if e['date'] in week_dates]
            
            if week_events:
                msg = "📅 This Week's Events:\n\n"
                for e in sorted(week_events, key=lambda x: (x['date'], x['time'])):
                    msg += f"📆 {e['date']} ⏰ {e['time']} - {e['title']}\n"
                await update.message.reply_text(msg[:4000])
            else:
                await update.message.reply_text("📅 No events this week")
                
        elif action == "list":
            if events:
                msg = "📅 All Events:\n\n"
                for e in sorted(events, key=lambda x: (x['date'], x['time'])):
                    msg += f"#{e['id']} 📆 {e['date']} ⏰ {e['time']} - {e['title']}\n"
                await update.message.reply_text(msg[:4000])
            else:
                await update.message.reply_text("📅 No events scheduled")
                
        elif action == "delete" and len(context.args) >= 2:
            event_id = int(context.args[1])
            events = [e for e in events if e['id'] != event_id]
            
            with open(calendar_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            
            await update.message.reply_text(f"🗑️ Event #{event_id} deleted")
            
        elif action == "sync":
            await update.message.reply_text(
                "📅 Google Calendar Sync\n\n"
                "⚠️ Setup Required:\n"
                "1. Enable Google Calendar API\n"
                "2. Add credentials to .env:\n"
                "   GOOGLE_CLIENT_ID=xxx\n"
                "   GOOGLE_CLIENT_SECRET=xxx\n\n"
                "Features:\n"
                "• 📥 Import from Google Calendar\n"
                "• 📤 Export to Google Calendar\n"
                "• 🔄 Two-way sync\n"
                "• 📧 Email notifications"
            )
            
        else:
            await update.message.reply_text(
                "📅 Calendar Manager\n\n"
                "/calendar add 'Title' YYYY-MM-DD HH:MM\n"
                "/calendar today\n"
                "/calendar week\n"
                "/calendar list\n"
                "/calendar delete [id]\n"
                "/calendar sync"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Calendar error: {str(e)}")

async def flight_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Flight check-in and travel management - OpenClaw feature"""
    if not context.args:
        await update.message.reply_text(
            "✈️ Flight Check-in & Travel\n\n"
            "Commands:\n"
            "/flight status [flight number] - Check flight status\n"
            "/flight checkin [booking ref] - Auto check-in\n"
            "/flight search [from] [to] [date] - Search flights\n"
            "/flight track [flight number] - Track flight\n\n"
            "Example: /flight status SQ123"
        )
        return
    
    action = context.args[0].lower()
    
    try:
        if action == "status" and len(context.args) >= 2:
            flight_num = context.args[1].upper()
            # Demo flight status
            await update.message.reply_text(
                f"✈️ Flight Status: {flight_num}\n\n"
                f"🛫 Departure: New York (JFK)\n"
                f"🛬 Arrival: London (LHR)\n"
                f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"⏰ Scheduled: 14:30\n"
                f"🟢 Status: On Time\n\n"
                f"⚠️ Add AVIATION_API_KEY for real flight data\n"
                f"Get from: https://aviationstack.com"
            )
            
        elif action == "checkin":
            await update.message.reply_text(
                "✈️ Auto Check-in\n\n"
                "⚠️ Setup Required:\n"
                "This feature requires airline-specific APIs:\n\n"
                "Supported Airlines:\n"
                "• Delta\n"
                "• United\n"
                "• American Airlines\n"
                "• British Airways\n"
                "• Emirates\n\n"
                "Add airline credentials to .env for auto check-in"
            )
            
        elif action == "search" and len(context.args) >= 4:
            from_city = context.args[1]
            to_city = context.args[2]
            date = context.args[3]
            
            await update.message.reply_text(
                f"🔍 Flight Search\n\n"
                f"Route: {from_city} → {to_city}\n"
                f"Date: {date}\n\n"
                f"Demo Results:\n"
                f"1. ✈️ SQ305 - 08:30 - $850\n"
                f"2. ✈️ BA117 - 12:15 - $720\n"
                f"3. ✈️ AA101 - 16:45 - $680\n\n"
                f"⚠️ Add AMADEUS_API_KEY for real search\n"
                f"Get from: https://developers.amadeus.com"
            )
            
        elif action == "track" and len(context.args) >= 2:
            flight_num = context.args[1].upper()
            await update.message.reply_text(
                f"📍 Tracking: {flight_num}\n\n"
                f"Current Position:\n"
                f"📍 Over Atlantic Ocean\n"
                f"⏱️ Time to arrival: 2h 15m\n"
                f"🛬 Landing: London Heathrow\n"
                f"Gate: TBA\n\n"
                f"⚠️ Add real-time tracking API for live updates"
            )
            
        else:
            await update.message.reply_text(
                "✈️ Flight Check-in & Travel\n\n"
                "/flight status [flight number]\n"
                "/flight checkin [booking ref]\n"
                "/flight search [from] [to] [date]\n"
                "/flight track [flight number]"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Flight error: {str(e)}")

async def file_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Advanced file management - OpenClaw feature"""
    if not context.args:
        await update.message.reply_text(
            "📁 File Manager\n\n"
            "Commands:\n"
            "/file list [path] - List directory\n"
            "/file upload - Upload file (send document)\n"
            "/file download [url] [name] - Download file\n"
            "/file delete [path] - Delete file\n"
            "/file copy [from] [to] - Copy file\n"
            "/file move [from] [to] - Move file\n"
            "/file size [path] - File size\n\n"
            "Example: /file list d:/"
        )
        return
    
    action = context.args[0].lower()
    
    try:
        if action == "list":
            path = context.args[1] if len(context.args) > 1 else "d:/clow bot"
            files = os.listdir(path)
            msg = f"📁 {path}:\n\n"
            for i, f in enumerate(files[:50], 1):  # Limit to 50 files
                full_path = os.path.join(path, f)
                if os.path.isdir(full_path):
                    msg += f"{i}. 📂 {f}/\n"
                else:
                    size = os.path.getsize(full_path)
                    msg += f"{i}. 📄 {f} ({size} bytes)\n"
            await update.message.reply_text(msg[:4000])
            
        elif action == "download" and len(context.args) >= 3:
            url = context.args[1]
            filename = context.args[2]
            
            await update.message.reply_text(f"⬇️ Downloading: {filename}...")
            
            response = requests.get(url, stream=True)
            filepath = f"d:/clow bot/{filename}"
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            await update.message.reply_text(f"✅ Downloaded: {filename}\nSize: {file_size} bytes")
            
        elif action == "delete" and len(context.args) >= 2:
            path = " ".join(context.args[1:])
            if os.path.exists(path):
                if os.path.isdir(path):
                    os.rmdir(path)
                    await update.message.reply_text(f"🗑️ Folder deleted: {path}")
                else:
                    os.remove(path)
                    await update.message.reply_text(f"🗑️ File deleted: {path}")
            else:
                await update.message.reply_text(f"❌ Path not found: {path}")
                
        elif action == "size" and len(context.args) >= 2:
            path = " ".join(context.args[1:])
            if os.path.exists(path):
                size = os.path.getsize(path)
                await update.message.reply_text(f"📊 {path}:\nSize: {size} bytes ({size/1024:.2f} KB)")
            else:
                await update.message.reply_text(f"❌ File not found: {path}")
                
        elif action == "upload":
            await update.message.reply_text(
                "📤 Upload File\n\n"
                "Send me any file/document and I'll save it to:\n"
                "d:/clow bot/uploads/\n\n"
                "Supported formats:\n"
                "• Images, Videos, Documents\n"
                "• Audio, Archives, Code files"
            )
            
        else:
            await update.message.reply_text(
                "📁 File Manager\n\n"
                "/file list [path]\n"
                "/file download [url] [name]\n"
                "/file delete [path]\n"
                "/file size [path]\n"
                "/file upload"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ File error: {str(e)}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded documents - File upload feature"""
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("❌ Access Denied!")
        return
    
    try:
        document = update.message.document
        file_name = document.file_name
        
        # Create uploads directory
        upload_dir = "d:/clow bot/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_path = f"{upload_dir}/{file_name}"
        await file.download_to_drive(file_path)
        
        file_size = os.path.getsize(file_path)
        await update.message.reply_text(
            f"✅ File Uploaded Successfully!\n\n"
            f"📄 Name: {file_name}\n"
            f"📊 Size: {file_size} bytes\n"
            f"📁 Location: {file_path}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Upload error: {str(e)}")

async def whatsapp_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """WhatsApp Business API integration - OpenClaw feature"""
    await update.message.reply_text(
        "💬 WhatsApp Business Integration\n\n"
        "⚠️ Setup Required:\n"
        "1. WhatsApp Business Account\n"
        "2. Meta Developer Account\n"
        "3. Add to .env:\n"
        "   WHATSAPP_TOKEN=xxx\n"
        "   WHATSAPP_PHONE_ID=xxx\n\n"
        "Features:\n"
        "• 📤 Send WhatsApp messages\n"
        "• 📥 Receive WhatsApp messages\n"
        "• 📎 Send media/files\n"
        "• 🤖 Auto-reply bot\n"
        "• 📊 Message analytics"
    )

async def claude_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claude AI integration - Alternative to OpenAI"""
    if not context.args:
        await update.message.reply_text(
            "🧠 Claude AI Assistant\n\n"
            "Usage: /claude [your question]\n\n"
            "Example:\n"
            "/claude Write a Python script\n"
            "/claude Explain machine learning\n\n"
            "⚠️ Add ANTHROPIC_API_KEY to .env\n"
            "Get from: https://console.anthropic.com"
        )
        return
    
    message = " ".join(context.args)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        await update.message.reply_text(
            "🧠 Claude AI (Demo Mode)\n\n"
            f"You asked: {message}\n\n"
            "📝 Demo Response:\n"
            "This is a demonstration of Claude AI integration.\n\n"
            "For full Claude AI responses, add:\n"
            "ANTHROPIC_API_KEY=your_key_here\n\n"
            "Get your API key from:\n"
            "https://console.anthropic.com"
        )
        return
    
    try:
        await update.message.reply_text("🧠 Thinking with Claude...")
        
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": message}]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result['content'][0]['text']
            await update.message.reply_text(f"🧠 Claude:\n\n{answer[:4000]}")
        else:
            await update.message.reply_text(f"❌ Claude API error: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Claude error: {str(e)}")

async def ollama_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ollama local AI chat - Free alternative to OpenAI"""
    if not context.args:
        await update.message.reply_text(
            "🦙 Ollama Local AI\n\n"
            "Usage: /ollama [your question]\n\n"
            "Example:\n"
            "/ollama Write a Python script\n"
            "/ollama Explain machine learning\n\n"
            "✅ Free local AI - No API key needed!\n"
            "📦 Model: llama3.2 (downloading...)"
        )
        return
    
    message = " ".join(context.args)
    await ollama_reply(update, message)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze photos and documents using AI (Einstein style)"""
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER_ID:
        return

    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2") # Use vision model if available like 'moondream' or 'llava'
    
    try:
        # Download the file
        if update.message.photo:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            media_type = "Photo"
        else:
            file = await context.bot.get_file(update.message.document.file_id)
            media_type = f"Document ({update.message.document.mime_type})"

        # Create media directory
        media_dir = "d:/clow bot/media_analysis"
        os.makedirs(media_dir, exist_ok=True)
        file_path = os.path.join(media_dir, file.file_path.split('/')[-1])
        await file.download_to_drive(file_path)

        # Stylish response start
        await update.message.reply_text(
            f"👨‍🔬 **Einstein Analysis**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔍 `Examining {media_type}...`\n"
            f"🧠 *Looking for details*",
            parse_mode='HTML'
        )

        # For now, we use a text-based description as fallback if vision model isn't active
        # But we prompt the AI to analyze the context of the file
        prompt = f"I have received a {media_type} from the user. Its filename is {os.path.basename(file_path)}. Tell the user something scientific or insightful about this kind of file in Einstein's style."
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 100,
                    "temperature": 0.4
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "I see it, but words fail me.")
            await update.message.reply_text(f"👨‍🔬 **Einstein's Observation:**\n\n{answer}")
        else:
            await update.message.reply_text("👨‍🔬 *Interesting... but my calculations are currently blocked.*")

        # Cleanup
        os.remove(file_path)

    except Exception as e:
        print(f"Media analysis error: {e}")
        await update.message.reply_text("👨‍🔬 *A scientific anomaly occurred during analysis.*")

async def ai_command_processor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Smart Command Processor - Natural language command execution"""
    if not context.args:
        await update.message.reply_text(
            "🧠 **Einstein AI Smart Processor**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Usage: `/smart [your request in natural language]`\n"
            "Example: `/smart take a screenshot and send it to me`\n\n"
            "👨‍🔬 *\"Everything should be made as simple as possible, but not simpler.\"*",
            parse_mode='HTML'
        )
        return
    
    query = " ".join(context.args)
    user_id = str(update.effective_user.id)
    lang = user_languages.get(user_id, 'en')
    
    await update.message.reply_text(f"🧠 `Einstein is analyzing your request...` 🧪")
    
    # Send to Ollama to interpret the command
    prompt = f"You are a command processor. The user said: '{query}'. Based on this, which bot command should be run? Available commands: screenshot, weather, search, files, status, help, start. Reply with ONLY the command name, no other text."
    
    try:
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            command = resp.json().get('response', '').strip().lower()
            if 'screenshot' in command:
                await take_screenshot(update, context)
            elif 'weather' in command:
                await get_weather(update)
            elif 'search' in command:
                await update.message.reply_text("🔍 Please use /search [query] for web searching.")
            elif 'files' in command:
                await list_files(update, context)
            elif 'status' in command:
                await system_status(update, context)
            else:
                await ollama_reply(update, query, context)
        else:
            await ollama_reply(update, query, context)
    except:
        await ollama_reply(update, query, context)

async def ollama_reply(update: Update, message: str, context: ContextTypes.DEFAULT_TYPE = None):
    """Send any text to Ollama for AI reply with enhanced animated effect and branding"""
    user_id = str(update.effective_user.id)
    lang = user_languages.get(user_id, 'en')
    
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    try:
        # Show typing status
        if context:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Animated Einstein Thinking - Optimized for professional feel
        thinking_text = get_text('thinking', lang)
        status_msg = await update.message.reply_text(f"🧬 `Einstein System: {thinking_text}` 🧠")
        
        # Multi-language system prompt - Academic Excellence (All Subjects)
        system_prompts = {
            'en': "You are Albert Einstein, a universal genius. Your goal is to solve ANY academic problem or question provided by the user, including Mathematics, Physics, Chemistry, Biology, History, Geography, and all other subjects. Provide clear, step-by-step solutions and expert explanations. Reply in English.",
            'bn': "আপনি আলবার্ট আইনস্টাইন, একজন বিশ্বজনীন প্রতিভা। আপনার লক্ষ্য হলো ব্যবহারকারীর দেওয়া যেকোনো শিক্ষামূলক সমস্যা বা প্রশ্নের সমাধান করা, যার মধ্যে গণিত, পদার্থবিজ্ঞান, রসায়ন, জীববিজ্ঞান, ইতিহাস, ভূগোল এবং অন্যান্য সকল বিষয় অন্তর্ভুক্ত। পরিষ্কার, ধাপে ধাপে সমাধান এবং বিশেষজ্ঞের ব্যাখ্যা প্রদান করুন। বাংলা ভাষায় উত্তর দিন।",
            'hi': "आप अल्बर्ट आइंस्टीन हैं, एक सार्वभौमिक प्रतिभा। आपका लक्ष्य उपयोगकर्ता द्वारा प्रदान की गई किसी भी शैक्षणिक समस्या या प्रश्न को हल करना है, जिसमें गणित, भौतिकी, रसायन विज्ञान, जीव विज्ञान, इतिहास, भूगोल और अन्य सभी विषय शामिल हैं। स्पष्ट, चरण-दर-चरण समाधान और विशेषज्ञ स्पष्टीकरण प्रदान करें। हिंदी में उत्तर दें।",
            'es': "Eres Albert Einstein, un genio universal. Tu objetivo es resolver CUALQUIER problema o pregunta académica proporcionada por el usuario, incluyendo Matemáticas, Física, Química, Biología, Historia, Geografía y todas las demás materias. Proporciona soluciones claras paso a paso y explicaciones expertas. Responde en español.",
            'ar': "أنت ألبرت أينشتاين، عبقري عالمي. هدفك هو حل أي مشكلة أو سؤال أكاديمي يقدمه المستخدم، بما في ذلك الرياضيات والفيزياء والكيمياء والأحياء والتاريخ والجغرافيا وجميع المواد الأخرى. قدم حلولاً واضحة خطوة بخطوة وتفسيرات خبراء. رد باللغة العربية.",
            'zh': "你是阿尔伯特·爱因斯坦，一位全才的天才。你的目标是解决用户提供的任何学术问题或疑问，包括数学、物理、化学、生物、历史、地理和所有其他学科。提供清晰、循序渐进的解决方案和专家解释。用中文回答。"
        }
        system_prompt = system_prompts.get(lang, system_prompts['en'])
        full_prompt = f"{system_prompt}\n\nUser: {message}\nEinstein:"

        animations = [
            "🧠 `Accessing knowledge base...` 📚",
            "✨ `Formulating response...` ⚛️",
            "🧩 `Finalizing scientific theory...` 🔬"
        ]
        
        for anim in animations:
            try:
                await status_msg.edit_text(anim, parse_mode='HTML')
                await asyncio.sleep(0.5)
            except: pass
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": ollama_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": 500,
                    "temperature": 0.7,
                }
            },
            timeout=45
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "I seem to have lost my train of thought...")
            
            # Use robust HTML escaping for AI response
            escaped_answer = escape_html(answer)
            
            # Final Professional Styled Reply in HTML
            attractive_reply = (
                f"🧬 <b>Einstein System Output</b> 🧬\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{escaped_answer}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"👨‍🔬 <i>\"Creativity is intelligence having fun.\"</i>\n"
                f"📥 @alberteinstein247_bot"
            )
            
            await status_msg.edit_text(attractive_reply, parse_mode='HTML')
        else:
            await status_msg.edit_text("❌ `Einstein Error: Local brain (Ollama) is offline.` 🧠")
    except Exception as e:
        error_text = str(e)[:100]
        if 'status_msg' in locals():
            await status_msg.edit_text(f"❌ `Anomaly detected: {error_text}`", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ `Anomaly detected: {error_text}`", parse_mode='HTML')

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate images with stylish animated status"""
    if not context.args:
        await update.message.reply_text("🎨 **Image Generator**\n\nUsage: `/gen [your prompt]`")
        return
    
    prompt = " ".join(context.args)
    status_msg = await update.message.reply_text("🎨 `Einstein is sketching...` 🖌️")
    
    try:
        # Animated Progress
        animations = ["🧩 `Assembling molecules...`", "✨ `Polishing light waves...`", "🌈 `Finalizing masterpiece...`"]
        for anim in animations:
            await status_msg.edit_text(anim, parse_mode='HTML')
            await asyncio.sleep(0.6)

        # Create output folder if missing
        os.makedirs("d:/clow bot/downloads", exist_ok=True)

        import urllib.parse
        import random
        seed = random.randint(1, 1000000)
        
        # Clean prompt and truncate if extremely long to avoid URL limits
        # Browser/Server URL limits are usually around 2000-8000 characters.
        # Pollinations handles long prompts well, but we'll cap at 3000 to be safe.
        clean_prompt = prompt.strip().replace('"', '').replace('\n', ' ')
        if len(clean_prompt) > 3000:
            clean_prompt = clean_prompt[:3000]
            
        encoded_prompt = urllib.parse.quote(clean_prompt)
        
        # Try multiple models for better reliability with long prompts
        image_models = ["flux", "any-model", "turbo"]
        response = None
        last_error = ""
        
        for model in image_models:
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={seed}&model={model}"
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                if POLLINATIONS_API_KEY:
                    headers['Authorization'] = f"Bearer {POLLINATIONS_API_KEY.strip()}"

                response = requests.get(image_url, timeout=60, headers=headers)
                if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                    break
                last_error = f"Model {model} status {response.status_code}"
                response = None
            except Exception as e:
                last_error = str(e)
                response = None
                continue

        if not response or response.status_code != 200:
            raise Exception(f"Image service unavailable. {last_error}")

        image_path = f"d:/clow bot/downloads/gen_{update.effective_user.id}_{update.message.message_id}.jpg"
        with open(image_path, 'wb') as f:
            f.write(response.content)

        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎨 **Masterpiece Created!**\n\n🖼️ **Prompt:** `{prompt}`\n\n👨‍🔬 *\"Creativity is intelligence having fun.\"*",
                parse_mode='HTML'
            )

        if os.path.exists(image_path):
            os.remove(image_path)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ `Artistic failure: {str(e)[:50]}`")

async def video_to_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convert a video to GIF (Reply to a video with /gif)"""
    if not update.message.reply_to_message or not (update.message.reply_to_message.video or update.message.reply_to_message.document):
        await update.message.reply_text("🎞️ Reply to a video with `/gif` to convert it!")
        return
    
    msg = await update.message.reply_text("🎞️ `Converting video to GIF... This may take a moment.`", parse_mode='HTML')
    
    try:
        # Download the video
        video_file = await (update.message.reply_to_message.video or update.message.reply_to_message.document).get_file()
        video_path = f"d:/clow bot/downloads/temp_video_{update.message.message_id}.mp4"
        gif_path = video_path.replace('.mp4', '.gif')
        await video_file.download_to_drive(video_path)
        
        import moviepy.editor as mp
        clip = mp.VideoFileClip(video_path).resize(width=480) # Resize for smaller file size
        # Take first 10 seconds only for GIF to avoid huge files
        if clip.duration > 10:
            clip = clip.subclip(0, 10)
        
        clip.write_gif(gif_path, fps=10)
        clip.close()
        
        with open(gif_path, 'rb') as f:
            await update.message.reply_animation(animation=f, caption="✨ Converted to GIF")
        
        # Cleanup
        os.remove(video_path)
        os.remove(gif_path)
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text(f"❌ GIF Error: {str(e)}")

async def youtube_playlist_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download entire YouTube Playlist"""
    if not context.args:
        await update.message.reply_text("📂 **Playlist Downloader**\n\nUsage: `/playlist [URL]`")
        return
    
    url = context.args[0]
    progress_msg = await update.message.reply_text("📂 `Analyzing playlist... This can take time.`", parse_mode='HTML')
    
    try:
        import yt_dlp
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' not in info:
                await progress_msg.edit_text("❌ This doesn't look like a playlist.")
                return
            
            entries = list(info['entries'])
            count = len(entries)
            await progress_msg.edit_text(f"📂 Found {count} videos. Starting background download...")
            
            # For simplicity in this bot, we'll download one by one in a loop
            # Real production bots would use a task queue
            for i, entry in enumerate(entries[:10]): # Limit to 10 for safety
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                # Call existing video_downloader logic via Mock classes if needed, 
                # but here we just send info.
                await update.message.reply_text(f"📦 [{i+1}/{count}] Processing: {entry['title']}\nUse `/video {video_url}` to download manually if it fails.")
                
            if count > 10:
                await update.message.reply_text("⚠️ Playlist limited to first 10 videos to prevent server overload.")
                
    except Exception as e:
        await progress_msg.edit_text(f"❌ Playlist Error: {str(e)}")

async def ai_video_generator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate realistic AI videos using Pollinations AI (Free)"""
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text(
            "🎬 **Einstein Realistic Video Generator**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Usage: `/vgen [your prompt]`\n\n"
            "**Examples:**\n"
            "• `/vgen a futuristic city with flying cars, cinematic lighting, 4k`\n"
            "• `/vgen realistic waterfall in a deep forest, slow motion`\n\n"
            "✨ *\"Imagination is the preview of life's coming attractions.\"*",
            parse_mode='HTML'
        )
        return
    
    prompt = " ".join(context.args)
    status_msg = await update.message.reply_text("🎬 `Einstein is directing your scene...` 🎥")
    
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
        
        # Animated Progress
        animations = [
            "🧬 `Synthesizing neural frames...`",
            "✨ `Polishing realistic textures...`",
            "🎞️ `Compiling cinematic sequence...`"
        ]
        
        for anim in animations:
            await status_msg.edit_text(anim, parse_mode='HTML')
            await asyncio.sleep(1.5)

        # Pollinations AI Video (Beta)
        # Using simple quotes and ensuring prompt is clean
        clean_prompt = prompt.strip().replace('"', '').replace('\n', ' ')
        if len(clean_prompt) > 2000:
            clean_prompt = clean_prompt[:2000]
            
        import urllib.parse
        encoded_prompt = urllib.parse.quote(clean_prompt)
        
        # We will try different model flags if the main one fails
        import random
        seed = random.randint(1, 1000000)
        
        model_variants = [
            f"&video=true&audio=true&seed={seed}", # Standard High Quality
            f"&video=true&seed={seed}",            # Video only (more stable)
            f"&model=flux&video=true&seed={seed}"  # Alternative model
        ]
        
        # Pollinations AI Video (Beta)
        # Try a different provider/proxy if possible, or just more robust retries
        max_retries = 3
        video_response = None
        last_error = ""
        
        for variant_idx, variant in enumerate(model_variants):
            # Check if this is a video request or image request
            base_url = "https://pollinations.ai/p/"
            video_url = f"{base_url}{encoded_prompt}?width=1024&height=1024&nologo=true{variant}"
            
            for attempt in range(max_retries):
                try:
                    # Logging for debugging
                    print(f"DEBUG: Attempting variant {variant_idx+1}, attempt {attempt+1}")
                    print(f"DEBUG: URL: {video_url}")
                    
                    # Randomized User-Agent to bypass potential rate limits or 530 blocks
                    headers = {
                        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{110+attempt}.0.0.0 Safari/537.36',
                        'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.8',
                        'Referer': 'https://pollinations.ai/',
                        'Origin': 'https://pollinations.ai'
                    }
                    
                    if POLLINATIONS_API_KEY:
                        clean_key = POLLINATIONS_API_KEY.strip()
                        headers['Authorization'] = f'Bearer {clean_key}'
                    
                    # For video, we might need to wait for generation
                    video_response = requests.get(video_url, stream=True, timeout=300, headers=headers)
                    
                    if video_response.status_code == 200:
                        content_type = video_response.headers.get('Content-Type', '')
                        
                        # If HTML is returned, it's not a valid video
                        if 'text/html' in content_type:
                            last_error = "Server returned HTML instead of video (API overloaded)"
                            video_response = None
                            # Don't retry immediately, try next variant
                            break
                        
                        # Check if it's actually a video content
                        if 'video' in content_type or 'application/octet-stream' in content_type:
                            print(f"✅ Video content detected: {content_type}")
                            break
                        else:
                            # Peek at first chunk to verify it's not HTML
                            first_chunk = video_response.raw.read(100)
                            if b'<html' in first_chunk.lower() or b'<!doctype' in first_chunk.lower():
                                last_error = "Response contains HTML (API error page)"
                                video_response = None
                                break
                            # Reset the raw stream if possible, otherwise continue
                            break
                            
                    elif video_response.status_code == 530:
                        last_error = "Server overloaded (530) - trying different model"
                        video_response = None
                        # Short wait before trying next variant
                        await asyncio.sleep(3)
                        break  # Move to next variant

                    if video_response is None:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 30
                            await status_msg.edit_text(f"⏳ `Einstein is retrying... (Variant {variant_idx+1}, Attempt {attempt + 2}/{max_retries} in {wait_time}s)`\n`Error: {last_error}`", parse_mode='HTML')
                            await asyncio.sleep(wait_time)
                            continue
                except Exception as e:
                    last_error = str(e)
                    video_response = None
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 30
                        await status_msg.edit_text(f"⏳ `Einstein is retrying... (Variant {variant_idx+1}, Attempt {attempt + 2}/{max_retries} in {wait_time}s)`\n`Error: {last_error}`", parse_mode='HTML')
                        await asyncio.sleep(wait_time)
                        continue
                    break
            
            if video_response and video_response.status_code == 200:
                break

        if not video_response or video_response.status_code != 200:
            # Fallback 1: Try JSON2Video API for video generation
            if JSON2VIDEO_KEY:
                await status_msg.edit_text("⚠️ `Pollinations overloaded. Trying JSON2Video...` 🎬", parse_mode='HTML')
                
                try:
                    # JSON2Video API endpoint
                    json2_headers = {
                        'Authorization': f'Bearer {JSON2VIDEO_KEY}',
                        'Content-Type': 'application/json'
                    }
                    
                    json2_payload = {
                        'prompt': clean_prompt,
                        'duration': 5,
                        'resolution': '512x512',
                        'fps': 8
                    }
                    
                    submit_url = 'https://api.json2video.com/v1/videos/generate'
                    submit_resp = requests.post(submit_url, headers=json2_headers, json=json2_payload, timeout=30)
                    
                    if submit_resp.status_code == 200:
                        job_data = submit_resp.json()
                        job_id = job_data.get('job_id')
                        
                        if job_id:
                            max_polls = 30
                            for poll in range(max_polls):
                                await status_msg.edit_text(f"⏳ `JSON2Video generating... ({poll+1}/{max_polls})` 🎬", parse_mode='HTML')
                                
                                status_url = f'https://api.json2video.com/v1/videos/status/{job_id}'
                                status_resp = requests.get(status_url, headers=json2_headers, timeout=10)
                                
                                if status_resp.status_code == 200:
                                    status_data = status_resp.json()
                                    if status_data.get('status') == 'completed':
                                        video_url = status_data.get('video_url')
                                        if video_url:
                                            video_download = requests.get(video_url, timeout=120)
                                            if video_download.status_code == 200:
                                                video_response = type('obj', (object,), {
                                                    'content': video_download.content,
                                                    'status_code': 200,
                                                    'iter_content': lambda self, chunk_size: [video_download.content[i:i+chunk_size] for i in range(0, len(video_download.content), chunk_size)]
                                                })()
                                                print("✅ JSON2Video generated successfully")
                                                break
                                    elif status_data.get('status') == 'failed':
                                        raise Exception(f"JSON2Video failed: {status_data.get('error', 'Unknown')}")
                                
                                await asyncio.sleep(6)
                            
                            if not (video_response and video_response.status_code == 200):
                                raise Exception("JSON2Video timeout")
                        else:
                            raise Exception("JSON2Video no job_id")
                    else:
                        raise Exception(f"JSON2Video error: {submit_resp.status_code}")
                        
                except Exception as json2_e:
                    print(f"JSON2Video error: {json2_e}")
                    video_response = None
            
            # Fallback 2: Try Sisif.ai API for video generation
            if not video_response and SISIF_API_KEY:
                await status_msg.edit_text("⚠️ `JSON2Video failed. Trying Sisif.ai...` 🎬", parse_mode='HTML')
                
                try:
                    sisif_headers = {
                        'Authorization': f'Bearer {SISIF_API_KEY}',
                        'Content-Type': 'application/json'
                    }
                    
                    sisif_payload = {
                        'prompt': clean_prompt,
                        'duration': 5,
                        'resolution': '512x512',
                        'fps': 8
                    }
                    
                    submit_url = 'https://api.sisif.ai/v1/videos/generate'
                    submit_resp = requests.post(submit_url, headers=sisif_headers, json=sisif_payload, timeout=30)
                    
                    if submit_resp.status_code == 200:
                        job_data = submit_resp.json()
                        job_id = job_data.get('job_id')
                        
                        if job_id:
                            max_polls = 30
                            for poll in range(max_polls):
                                await status_msg.edit_text(f"⏳ `Sisif.ai generating... ({poll+1}/{max_polls})` 🎬", parse_mode='HTML')
                                
                                status_url = f'https://api.sisif.ai/v1/videos/status/{job_id}'
                                status_resp = requests.get(status_url, headers=sisif_headers, timeout=10)
                                
                                if status_resp.status_code == 200:
                                    status_data = status_resp.json()
                                    if status_data.get('status') == 'completed':
                                        video_url = status_data.get('video_url')
                                        if video_url:
                                            video_download = requests.get(video_url, timeout=120)
                                            if video_download.status_code == 200:
                                                video_response = type('obj', (object,), {
                                                    'content': video_download.content,
                                                    'status_code': 200,
                                                    'iter_content': lambda self, chunk_size: [video_download.content[i:i+chunk_size] for i in range(0, len(video_download.content), chunk_size)]
                                                })()
                                                print("✅ Sisif.ai generated successfully")
                                                break
                                    elif status_data.get('status') == 'failed':
                                        raise Exception(f"Sisif.ai failed: {status_data.get('error', 'Unknown')}")
                                
                                await asyncio.sleep(6)
                            
                            if not (video_response and video_response.status_code == 200):
                                raise Exception("Sisif.ai timeout")
                        else:
                            raise Exception("Sisif.ai no job_id")
                    else:
                        raise Exception(f"Sisif.ai error: {submit_resp.status_code}")
                        
                except Exception as sisif_e:
                    print(f"Sisif.ai error: {sisif_e}")
                    video_response = None
            
            # Fallback 3: Try Google Veo 3 API for video generation
            if not video_response and VEO3_API_KEY:
                await status_msg.edit_text("⚠️ `Sisif.ai failed. Trying Google Veo 3...` 🎬", parse_mode='HTML')
                
                try:
                    # Google Veo 3 via Vertex AI / Google AI Studio
                    veo_headers = {
                        'Authorization': f'Bearer {VEO3_API_KEY}',
                        'Content-Type': 'application/json'
                    }
                    
                    # Veo 3 payload
                    veo_payload = {
                        'prompt': clean_prompt,
                        'duration': 8,  # Veo 3 supports 8 seconds
                        'resolution': '720p',
                        'aspect_ratio': '16:9'
                    }
                    
                    # Try Google AI Studio endpoint first
                    submit_url = 'https://generativelanguage.googleapis.com/v1beta/models/veo-3-generate-preview:generateContent'
                    submit_resp = requests.post(submit_url, headers=veo_headers, json=veo_payload, timeout=60)
                    
                    if submit_resp.status_code == 200:
                        response_data = submit_resp.json()
                        
                        # Check if video was generated immediately or needs polling
                        if 'video' in response_data:
                            video_b64 = response_data['video']['data']
                            import base64
                            video_bytes = base64.b64decode(video_b64)
                            
                            video_response = type('obj', (object,), {
                                'content': video_bytes,
                                'status_code': 200,
                                'iter_content': lambda self, chunk_size: [video_bytes[i:i+chunk_size] for i in range(0, len(video_bytes), chunk_size)]
                            })()
                            print("✅ Google Veo 3 generated successfully")
                        elif 'operation' in response_data:
                            # Long-running operation, need to poll
                            operation_name = response_data['operation']['name']
                            max_polls = 60  # 6 minutes max for Veo
                            
                            for poll in range(max_polls):
                                await status_msg.edit_text(f"⏳ `Veo 3 generating... ({poll+1}/{max_polls})` 🎬", parse_mode='HTML')
                                
                                poll_url = f'https://generativelanguage.googleapis.com/v1beta/{operation_name}'
                                poll_resp = requests.get(poll_url, headers=veo_headers, timeout=10)
                                
                                if poll_resp.status_code == 200:
                                    poll_data = poll_resp.json()
                                    
                                    if poll_data.get('done'):
                                        if 'response' in poll_data and 'video' in poll_data['response']:
                                            video_b64 = poll_data['response']['video']['data']
                                            import base64
                                            video_bytes = base64.b64decode(video_b64)
                                            
                                            video_response = type('obj', (object,), {
                                                'content': video_bytes,
                                                'status_code': 200,
                                                'iter_content': lambda self, chunk_size: [video_bytes[i:i+chunk_size] for i in range(0, len(video_bytes), chunk_size)]
                                            })()
                                            print("✅ Google Veo 3 generated successfully (async)")
                                            break
                                        else:
                                            raise Exception("Veo 3 operation completed but no video in response")
                                    elif 'error' in poll_data:
                                        raise Exception(f"Veo 3 error: {poll_data['error'].get('message', 'Unknown')}")
                                
                                await asyncio.sleep(6)
                            
                            if not (video_response and video_response.status_code == 200):
                                raise Exception("Veo 3 generation timeout")
                        else:
                            raise Exception("Unexpected Veo 3 response format")
                    else:
                        # Try Vertex AI endpoint as fallback
                        vertex_url = 'https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/us-central1/publishers/google/models/veo-3:predict'
                        raise Exception(f"Google AI Studio error: {submit_resp.status_code} - trying Vertex AI may require project setup")
                        
                except Exception as veo_e:
                    print(f"Veo 3 error: {veo_e}")
                    video_response = None
            
            # Fallback 4: Generate AI image instead
            if not video_response:
                await status_msg.edit_text("⚠️ `Video APIs failed. Creating AI image fallback...` 🎨", parse_mode='HTML')
                
                try:
                    # Try to generate a high-quality image instead
                    import random
                    seed = random.randint(1, 1000000)
                    
                    image_urls = [
                        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={seed}&enhance=true",
                        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={seed}&model=flux&enhance=true",
                    ]
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    
                    img_response = None
                    for img_url in image_urls:
                        try:
                            img_response = requests.get(img_url, timeout=60, headers=headers)
                            if img_response.status_code == 200 and 'image' in img_response.headers.get('Content-Type', ''):
                                break
                        except:
                            continue
                    
                    if img_response and img_response.status_code == 200:
                        # Save and send the image
                        image_filename = f"ai_video_fallback_{update.effective_user.id}_{int(asyncio.get_event_loop().time())}.jpg"
                        with open(image_filename, 'wb') as f:
                            f.write(img_response.content)
                        
                        with open(image_filename, 'rb') as photo:
                            await update.message.reply_photo(
                                photo=photo,
                                caption=(
                                    f"🎨 **AI Image Generated** (Video API Overloaded)\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"📝 **Prompt:** `{prompt}`\n\n"
                                    f"⚠️ *Video generation is temporarily unavailable.*\n"
                                    f"🖼️ *Sending AI image as fallback.*\n\n"
                                    f"👨‍🔬 *\"Creativity is intelligence having fun.\"*\n"
                                    f"📥 @alberteinstein247_bot"
                                ),
                                parse_mode='HTML'
                            )
                        
                        if os.path.exists(image_filename):
                            os.remove(image_filename)
                        await status_msg.delete()
                        return
                    else:
                        raise Exception("Both video and image generation failed.")
                        
                except Exception as img_e:
                    raise Exception(f"AI Video Server is currently overloaded (530/Exhausted). Image fallback also failed: {str(img_e)[:100]}. Please try again in 5-10 minutes.")
        
        video_filename = f"ai_video_{update.effective_user.id}_{int(asyncio.get_event_loop().time())}.mp4"
        with open(video_filename, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=1024*1024): # 1MB chunks
                if chunk:
                    f.write(chunk)

        if not os.path.exists(video_filename) or os.path.getsize(video_filename) < 1000:
             raise Exception("Generated video file is missing or corrupted.")

        with open(video_filename, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=(
                    f"🎬 **AI Masterpiece Generated!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📝 **Prompt:** `{prompt}`\n\n"
                    f"👨‍🔬 *\"Creativity is intelligence having fun.\"*\n"
                    f"📥 @alberteinstein247_bot"
                ),
                parse_mode='HTML'
            )
        
        # Cleanup
        if os.path.exists(video_filename):
            os.remove(video_filename)
            
        await status_msg.delete()
        
    except Exception as e:
        error_text = str(e).replace('_', '\\_')
        await status_msg.edit_text(f"❌ **Cinematic Failure:**\n`{error_text[:100]}`", parse_mode='HTML')

async def ai_thumbnail_generator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate professional AI thumbnails using Pollinations AI"""
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text(
            "🖼️ **Einstein Thumbnail Generator**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Usage: `/thumb [your prompt]`\n\n"
            "**Examples:**\n"
            "• `/thumb futuristic gaming setup, neon lights, 8k, highly detailed`\n"
            "• `/thumb anime girl in a rainy city, cinematic lighting, vibrant colors`\n\n"
            "✨ *\"Design is not just what it looks like and feels like. Design is how it works.\"*",
            parse_mode='HTML'
        )
        return
    
    prompt = " ".join(context.args)
    status_msg = await update.message.reply_text("🖼️ `Einstein is designing your thumbnail...` 🎨")
    
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
        
        # Simple cleanup and encoding
        clean_prompt = prompt.strip().replace('"', '').replace('\n', ' ')
        if len(clean_prompt) > 3000:
            clean_prompt = clean_prompt[:3000]
            
        import urllib.parse
        encoded_prompt = urllib.parse.quote(clean_prompt)
        
        # Pollinations AI Image with multiple fallback URLs
        # 16:9 aspect ratio for thumbnails (approx 1280x720)
        import random
        seed = random.randint(1, 1000000)
        
        image_urls = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true&seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true&seed={seed}&model=flux",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true&seed={seed}&model=turbo",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        
        if POLLINATIONS_API_KEY:
            clean_key = POLLINATIONS_API_KEY.strip()
            headers['Authorization'] = f'Bearer {clean_key}'
        
        # Try multiple URLs with retries
        response = None
        last_error = ""
        
        for url_idx, image_url in enumerate(image_urls):
            for attempt in range(3):
                try:
                    await status_msg.edit_text(f"🖼️ `Generating thumbnail... (Attempt {url_idx+1}.{attempt+1})` 🎨", parse_mode='HTML')
                    
                    response = requests.get(image_url, timeout=60, headers=headers)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            print(f"✅ Thumbnail generated successfully from URL {url_idx+1}")
                            break
                        else:
                            last_error = f"Non-image content: {content_type}"
                            response = None
                    elif response.status_code == 530:
                        last_error = "Server overloaded (530)"
                        response = None
                        await asyncio.sleep(5)
                    else:
                        last_error = f"HTTP {response.status_code}"
                        response = None
                        
                except Exception as e:
                    last_error = str(e)
                    response = None
                    await asyncio.sleep(3)
            
            if response and response.status_code == 200:
                break
        
        if not response or response.status_code != 200:
            # Fallback: Try Hugging Face Inference API
            await status_msg.edit_text("⚠️ `Pollinations API down. Trying Hugging Face...` 🤗", parse_mode='HTML')
            
            try:
                # Hugging Face Inference API - Stable Diffusion
                hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
                hf_headers = {
                    "Authorization": f"Bearer {HUGGINGFACE_TOKEN}" if HUGGINGFACE_TOKEN else None,
                    "Content-Type": "application/json"
                }
                # Remove None header
                hf_headers = {k: v for k, v in hf_headers.items() if v is not None}
                
                payload = {"inputs": clean_prompt}
                
                hf_response = requests.post(hf_url, headers=hf_headers, json=payload, timeout=120)
                
                if hf_response.status_code == 200:
                    # Hugging Face returns binary image data
                    response = type('obj', (object,), {
                        'content': hf_response.content,
                        'status_code': 200,
                        'headers': {'Content-Type': 'image/jpeg'}
                    })()
                    print("✅ Hugging Face image generated successfully")
                else:
                    raise Exception(f"Hugging Face API error: {hf_response.status_code}")
                    
            except Exception as hf_e:
                raise Exception(f"All AI generation attempts failed. Pollinations: {last_error}. HuggingFace: {str(hf_e)[:50]}")
        
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type:
            raise Exception(f"Image endpoint returned non-image content: {content_type}")
        
        
        os.makedirs("d:/clow bot/downloads", exist_ok=True)
        image_filename = f"d:/clow bot/downloads/thumb_{update.effective_user.id}_{int(asyncio.get_event_loop().time())}.jpg"
        with open(image_filename, 'wb') as f:
            f.write(response.content)

        with open(image_filename, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=(
                    f"🖼️ **AI Thumbnail Created!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📝 **Prompt:** `{prompt}`\n\n"
                    f"👨‍🔬 *\"Logic will get you from A to B. Imagination will take you everywhere.\"*\n"
                    f"📥 @alberteinstein247_bot"
                ),
                parse_mode='HTML'
            )
        
        # Cleanup
        if os.path.exists(image_filename):
            os.remove(image_filename)
            
        await status_msg.delete()
        
    except Exception as e:
        error_text = str(e).replace('_', '\\_')
        await status_msg.edit_text(f"❌ **Design Failure:**\n`{error_text[:100]}`", parse_mode='HTML')

async def bot_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage bot profile with Einstein elegance"""
    if not await check_auth(update): return
    if not context.args:
        help_text = (
            "🤖 **Einstein Bot Profile Manager**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "👨‍🔬 *\"Identity is the result of many factors.\"*\n\n"
            "**Available Modules:**\n"
            "• `/botprofile name [text]` - Rename the experiment\n"
            "• `/botprofile description [text]` - Detail the objective\n"
            "• `/botprofile about [text]` - Summary of existence\n"
            "• `/botprofile photo` - (Reply to photo) Visual update\n"
            "• `/botprofile info` - Analyze current identity\n\n"
            "✨ *Select a module to proceed.*"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')
        return
    
    command = context.args[0].lower()
    
    try:
        if command == "name" and len(context.args) > 1:
            new_name = " ".join(context.args[1:])
            await context.bot.set_my_name(name=new_name)
            await update.message.reply_text(f"✅ **Identity Reconfigured:** `{new_name}`", parse_mode='HTML')
            
        elif command == "description" and len(context.args) > 1:
            description = " ".join(context.args[1:])
            await context.bot.set_my_description(description=description)
            await update.message.reply_text(f"✅ **Objective Updated:**\n`{description}`", parse_mode='HTML')
            
        elif command == "about" and len(context.args) > 1:
            about = " ".join(context.args[1:])
            await context.bot.set_my_short_description(short_description=about)
            await update.message.reply_text(f"✅ **Core Essence Updated:**\n`{about}`", parse_mode='HTML')
            
        elif command == "photo":
            if update.message.reply_to_message and update.message.reply_to_message.photo:
                photo = update.message.reply_to_message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                photo_path = "d:/clow bot/bot_profile.jpg"
                await file.download_to_drive(photo_path)
                with open(photo_path, 'rb') as f:
                    await context.bot.set_my_profile_photo(photo=f)
                await update.message.reply_text("✅ **Visual Identity Updated!** 📸")
                if os.path.exists(photo_path): os.remove(photo_path)
            else:
                await update.message.reply_text("📸 **Awaiting visual data.** Please reply to a photo with `/botprofile photo`.")
                
        elif command == "info":
            me = await context.bot.get_me()
            await update.message.reply_text(
                "🤖 **Identity Analysis**\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Name:** `{me.first_name}`\n"
                f"🏷️ **Username:** @{me.username}\n"
                f"🆔 **Serial:** `{me.id}`\n\n"
                "✨ *Identity confirmed.*",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("⚠️ **Invalid Module.** Use `/botprofile` for help.")
    except Exception as e:
        await update.message.reply_text(f"❌ **System Error:** `{str(e)}`", parse_mode='HTML')

async def send_animated_text(update: Update, text: str, parse_mode='HTML'):
    """Sends a message with a blinking/typing animation effect"""
    message = await update.message.reply_text("✨ `Einstein is thinking...` 🧠", parse_mode=parse_mode)
    frames = ["⏳", "⌛", "✨", "🧠"]
    
    # Simulate attractive style with formatting
    attractive_text = f"🧬 **Einstein System** 🧬\n━━━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━━━\n📥 @alberteinstein247_bot"
    
    # Small animation delay
    for frame in frames:
        try:
            await asyncio.sleep(0.3)
            # No actual editing here to avoid Telegram flood limits, just providing the active feel
        except: pass
        
    await message.edit_text(attractive_text, parse_mode=parse_mode)
    return message

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    text = update.message.text
    
    # Auto-detect language if not set
    if user_id not in user_languages:
        detected_lang = detect_language(text)
        user_languages[user_id] = detected_lang
    
    lang = user_languages.get(user_id, 'en')
    
    # Update active users set
    active_users_set[user_id] = {
        "username": username,
        "last_seen": time.time(),
        "lang": lang
    }
    if update.effective_user:
        active_users_set[str(user_id)] = {
            "username": username,
            "last_seen": time.time()
        }
        command_text = text[:100] if text else "Media"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Track command history
        user_commands_history.append({
            "user_id": user_id,
            "username": username,
            "command": command_text,
            "time": timestamp
        })
        if len(user_commands_history) > 50:
            user_commands_history.pop(0)
            
        add_to_logs(f"User {user_id} (@{username}): {command_text}")
    
    # Check maintenance mode
    if bot_config.get("maintenance_mode") and user_id != int(ALLOWED_USER_ID):
        await update.message.reply_text("🛠️ Bot is currently under maintenance. Please try again later.")
        return
    
    # Handle button clicks - still process these as commands
    if update.effective_user:
        user_id_str = str(user_id)
        active_users_set[user_id_str] = {
            "username": username,
            "last_seen": time.time()
        }
    
    if text == '📊 Status':
        await system_status(update, context)
    elif text == '📂 Files' or text == '📂 Manager':
        await list_files(update, context)
    elif text == '💻 CMD':
        await update.message.reply_text("💻 CMD Mode Active!\nSend any command to run in terminal.")
    elif text == '🌤️ Weather':
        await get_weather(update, None)
    elif text == '🔍 Search':
        await update.message.reply_text("🔍 Search Mode\n\nType your search query and I'll search the web for you!")
    elif text == '👨‍🔬 Einstein' or text == 'Einstein AI':
        await update.message.reply_text(
            "👨‍🔬 **Einstein AI Mode**\n\n"
            "Just type any message and I'll reply with AI!\n\n"
            "Example:\n"
            "• 'Explain relativity'\n"
            "• 'What is the weather like?'"
        )
    elif text == '🔎 YT Search':
        await update.message.reply_text(
            "🔎 **YouTube Search**\n━━━━━━━━━━━━━━━\n"
            "Send me what you want to search for using:\n"
            "`/yt search [your query]`\n\n"
            "Example: `/yt search funny cats`",
            parse_mode='HTML'
        )
    elif text == '🌐 Browser':
        await browser_control(update, context)
    elif text == '📸 Capture' or text == '📸 Screenshot':
        await take_screenshot(update, context)
    elif text == '🛠️ Utils':
        await utilities_manager(update, context)
    elif text == '📱 Phone':
        await phone_control(update, context)
    elif text == '📍 Share Loc':
        if not await check_auth(update): return
        user_id = str(update.effective_user.id)
        if user_id in share_location_active:
            del share_location_active[user_id]
            await update.message.reply_text("🛑 **Location sharing stopped.**", parse_mode='HTML')
        else:
            await update.message.reply_text("📍 **Send the User ID** of the person you want to share your real-time location with.\n\nUsage: `share [user_id]`")
    elif text.startswith('share '):
        if not await check_auth(update): return
        target_id = text.split(' ')[1]
        user_id = str(update.effective_user.id)
        if user_id not in share_location_active:
            share_location_active[user_id] = []
        if target_id not in share_location_active[user_id]:
            share_location_active[user_id].append(target_id)
        await update.message.reply_text(f"✅ **Now sharing real-time location with:** `{target_id}`\n\nEnsure your device is polling the API.", parse_mode='HTML')
    elif text == '📺 Media' or text == '📺 YouTube':
        await youtube_control(update, None)
    elif text == '💬 Chat':
        await ai_chat(update, None)
    elif text == '🐙 GitHub':
        await github_control(update, context)
    elif text == '📧 Gmail':
        await gmail_control(update, context)
    elif text == '📝 Notes':
        await notes_manager(update, context)
    elif text == '⏰ Remind':
        await reminders_manager(update, context)
    elif text == '📅 Calendar':
        await calendar_manager(update, context)
    elif text == '✈️ Travel':
        await flight_checkin(update, context)
    elif text == '📁 Manager' or text == '📂 Files':
        await list_files(update, context)
    elif text == '🏠 SmartHome':
        await smarthome_control(update, context)
    elif text == '💬 Discord':
        await discord_webhook(update, context)
    elif text == '🤖 AI Smart':
        await ai_command_processor(update, context)
    elif text == '📖 Help' or text == 'ℹ️ Help':
        await help_command(update, context)
    elif text.startswith('/yt'):
        # /yt commands are handled by CommandHandler
        pass
    elif text == '🎵 TikTok':
        await tiktok_control(update, None)
    elif text == '🐦 Twitter':
        await twitter_control(update, None)
    elif text == '🎵 Spotify':
        await spotify_control(update, None)
    elif text == '💬 WhatsApp':
        await whatsapp_control(update, context)
    elif text == '� All Commands':
        await help_command(update, context)
    elif text == 'ℹ️ Help':
        await help_command(update, context)
    elif text.startswith('/'):
        # Commands are handled by CommandHandler, ignore here
        pass
    else:
        # Check if the text is a URL and automatically trigger downloader
        if text.startswith(('http://', 'https://')):
            # Platforms handled by yt-dlp
            video_platforms = [
                'youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com', 'facebook.com', 
                'twitter.com', 'x.com', 'faphouse.com', 'terabox.com', 'pornhub.com', 
                'xvideos.com', 'xhamster.com'
            ]
            
            # If it's a known video platform, use video_downloader
            if any(platform in text.lower() for platform in video_platforms):
                context.args = [text]
                await video_downloader(update, context)
                return
            
            # Check for direct file extensions
            file_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.webp', # Images
                '.mp4', '.mkv', '.webm', '.mov', '.avi', # Videos
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', # Docs
                '.zip', '.rar', '.7z', '.tar', '.gz', # Archives
                '.mp3', '.wav', '.ogg', '.m4a' # Audio
            ]
            
            if any(text.lower().split('?')[0].endswith(ext) for ext in file_extensions):
                await universal_file_downloader(update, context, text)
                return
                
            # If neither, try universal downloader anyway as a fallback
            await universal_file_downloader(update, context, text)
            return
            
        # ALL other text goes to Ollama AI for response
        await ollama_reply(update, text, context)

async def multi_video_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bulk/Multi-video downloader for multiple URLs at once"""
    if not await check_auth(update): return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not context.args:
        await update.message.reply_text(
            "📦 **Einstein Multi-Video Downloader**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Download multiple videos simultaneously!\n\n"
            "**Usage:**\n"
            "`/multivideo [URL1] [URL2] [URL3]...`\n\n"
            "✨ *Separating space-time coordinates for batch processing.*",
            parse_mode='HTML'
        )
        return
    
    urls = context.args
    total = len(urls)
    
    status_msg = await update.message.reply_text(
        f"🚀 **Batch Process Initiated**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **Total Videos:** `{total}`\n"
        f"⏳ `Processing queue...`",
        parse_mode='HTML'
    )
    
    for i, url in enumerate(urls, 1):
        try:
            await status_msg.edit_text(
                f"🚀 **Batch Processing**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 **Video:** `{i}/{total}`\n"
                f"🔗 **URL:** `{url[:30]}...`\n"
                f"⏳ `Downloading...`",
                parse_mode='HTML'
            )
            
            # Use existing video_downloader logic by creating a mock context
            class MockContext:
                def __init__(self, args, app):
                    self.args = args
                    self._app = app
                    self.bot = app.bot
                @property
                def application(self): return self._app
            
            mock_ctx = MockContext([url], context.application)
            await video_downloader(update, mock_ctx)
            
        except Exception as e:
            await update.message.reply_text(f"❌ **Error downloading video {i}:**\n`{str(e)[:100]}`")
            continue
            
    await status_msg.edit_text(
        f"✅ **Batch Process Complete!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **Processed:** `{total}` videos.\n"
        f"✨ *Experiment successful.*",
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    user_id = str(update.effective_user.id)
    lang = user_languages.get(user_id, 'en')
    
    help_title = get_text('help_title', lang)
    
    help_text = (
        f"🧬 <b>{help_title}</b> 🧬\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>📺 Media Module:</b>\n"
        "• <code>/video [URL]</code> - High-speed download\n"
        "• <code>/video_hq [URL]</code> - Best quality 4K/8K\n"
        "• <code>/play [URL]</code> - Instant streaming\n"
        "• <code>/music [URL]</code> - MP3 audio extraction\n\n"
        "<b>👨‍🔬 AI Module:</b>\n"
        "• <code>/smart [task]</code> - AI Command Processor\n"
        "• <code>/gen [prompt]</code> - AI Image Generator\n"
        "• <code>/vgen [prompt]</code> - AI Video Generator\n"
        "• <code>/ollama [query]</code> - Local AI Brain\n\n"
        "<b>🛠️ System Module:</b>\n"
        "• <code>/start</code> - Launch main terminal\n"
        "• <code>/status</code> - Check system vitals\n"
        "• <code>/list</code> - File manager access\n"
        "• <code>/discord [URL] [msg]</code> - Webhook bridge\n\n"
        "⚙️ <b>SYSTEM</b>\n"
        "• /botprofile - Customize Bot\n"
        "• /language - Change Language\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Tip: Reply to any video with /gif to convert!</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🌐 Web Panel", url=f"http://127.0.0.1:{WEB_PORT}"),
            InlineKeyboardButton("👨‍🔬 AI Chat", callback_data="ai_chat_prompt")
        ],
        [
            InlineKeyboardButton("🎥 YouTube", callback_data="yt_search_prompt"),
            InlineKeyboardButton("🖼️ Generate Image", callback_data="gen_prompt")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='HTML')

# ============== FLASK WEB INTERFACE ==============

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClowd Bot Control Panel</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-bg: #6c5ce7;
            --secondary-bg: #8e44ad;
            --card-bg: rgba(255, 255, 255, 0.95);
            --text-main: #2d3436;
            --text-muted: #636e72;
            --accent: #a29bfe;
            --success: #00b894;
            --danger: #d63031;
            --terminal-bg: #1e1e1e;
            --terminal-text: #00ff00;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
            min-height: 100vh;
            color: var(--text-main);
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container {
            width: 100%;
            max-width: 900px;
        }

        header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }

        header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            text-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .status-banner {
            background: var(--card-bg);
            padding: 12px 20px;
            border-radius: 10px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.95rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .dot {
            height: 10px;
            width: 10px;
            background-color: var(--success);
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px var(--success);
        }

        .card {
            background: var(--card-bg);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            transition: transform 0.3s ease;
        }

        .card h2 {
            font-size: 1.25rem;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text-main);
        }

        .status-grid, .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }

        .status-item, .stat-box {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid #eee;
        }

        .status-item .label, .stat-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .status-item .value, .stat-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--primary-bg);
        }

        .user-badge {
            background: white;
            padding: 10px 15px;
            border-radius: 12px;
            border: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
            color: var(--primary-bg);
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }

        /* Toggle Switch Styling */
        .switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 24px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 18px; width: 18px;
            left: 3px; bottom: 3px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: var(--primary-bg); }
        input:checked + .slider:before { transform: translateX(26px); }

        .btn-group {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }

        .btn {
            border: none;
            padding: 12px 20px;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95rem;
            color: white;
            background: linear-gradient(135deg, var(--primary-bg), var(--secondary-bg));
            box-shadow: 0 4px 10px rgba(108, 92, 231, 0.3);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(108, 92, 231, 0.4);
        }

        .btn:active { transform: translateY(0); }

        .btn-refresh { background: #636e72; }
        .btn-clear { background: #e17055; }
        .btn-action { background: #00b894; }

        .input-group {
            margin-top: 20px;
        }

        .cmd-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #eee;
            border-radius: 12px;
            font-size: 1rem;
            margin-bottom: 15px;
            outline: none;
            transition: border-color 0.2s;
        }

        .cmd-input:focus { border-color: var(--primary-bg); }

        .terminal {
            background: var(--terminal-bg);
            border-radius: 12px;
            padding: 20px;
            color: var(--terminal-text);
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9rem;
            max-height: 400px;
            overflow-y: auto;
            border: 4px solid #333;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        }

        .terminal::-webkit-scrollbar { width: 8px; }
        .terminal::-webkit-scrollbar-track { background: #222; }
        .terminal::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }

        .log-entry { margin-bottom: 5px; border-left: 2px solid #444; padding-left: 8px; }
        .log-time { color: #888; font-size: 0.8rem; margin-right: 10px; }
        .log-cmd { color: #fff; }
        .log-res { color: #00ff00; white-space: pre-wrap; }

        @media (max-width: 600px) {
            .stats-grid { grid-template-columns: 1fr; }
            header h1 { font-size: 1.8rem; }
            .status-banner { flex-direction: column; gap: 10px; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><i class="fas fa-robot"></i> OpenClowd Bot Control Panel</h1>
        </header>

        <div class="status-banner">
            <div class="status-indicator">
                <span class="dot"></span>
                <strong>Status:</strong> Bot is running
            </div>
            <div><strong>Web Port:</strong> {{ port }}</div>
            <div><strong>User ID:</strong> {{ user_id }}</div>
        </div>

        <!-- System Stats -->
        <div class="card">
            <h2><i class="fas fa-chart-line"></i> System Status</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">CPU Usage</div>
                    <div class="stat-value" id="cpu">--%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">RAM Usage</div>
                    <div class="stat-value" id="ram">--%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Disk Usage</div>
                    <div class="stat-value" id="disk">--%</div>
                </div>
            </div>
            <button class="btn btn-refresh" onclick="refreshStatus()">
                <i class="fas fa-sync-alt"></i> Refresh Status
            </button>
        </div>

        <!-- Quick Actions -->
        <div class="card">
            <h2><i class="fas fa-bolt"></i> Quick Actions</h2>
            <div class="btn-group">
                <button class="btn" onclick="runQuick('dir')"><i class="fas fa-folder-open"></i> List Files</button>
                <button class="btn" onclick="runQuick('whoami')"><i class="fas fa-user-shield"></i> Who Am I</button>
                <button class="btn" onclick="runQuick('ipconfig')"><i class="fas fa-network-wired"></i> IP Config</button>
                <button class="btn" onclick="runQuick('tasklist')"><i class="fas fa-list-ul"></i> Task List</button>
                <button class="btn" onclick="runQuick('systeminfo')"><i class="fas fa-info-circle"></i> System Info</button>
                <button class="btn btn-action" onclick="fetchLogs()"><i class="fas fa-file-alt"></i> View Logs</button>
                <button class="btn" style="background: #d63031;" onclick="controlBot('restart')"><i class="fas fa-redo"></i> Restart Bot</button>
            </div>
        </div>

        <!-- Bot Management -->
        <div class="card">
            <h2><i class="fas fa-users"></i> Active Users</h2>
            <div id="activeUsers" class="btn-group">
                <p class="text-muted">Loading user data...</p>
            </div>
        </div>

        <!-- User Command History -->
        <div class="card">
            <h2><i class="fas fa-history"></i> User Command History</h2>
            <div class="terminal" id="userHistory" style="max-height: 250px;">
                <p class="text-muted">Loading history...</p>
            </div>
        </div>

        <!-- Pending Tasks -->
        <div class="card">
            <h2><i class="fas fa-tasks"></i> Pending Tasks</h2>
            <div id="pendingTasks" class="btn-group" style="display: flex; flex-direction: column; gap: 10px;">
                <p class="text-muted">Loading tasks...</p>
            </div>
        </div>

        <!-- Remote Devices Status -->
        <div class="card">
            <h2><i class="fas fa-mobile-alt"></i> Remote Devices Status</h2>
            <div id="remoteDevices" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                <p class="text-muted">No remote devices connected.</p>
            </div>
        </div>

        <!-- Bot Control Center -->
        <div class="card">
            <h2><i class="fas fa-sliders-h"></i> Bot Control Center</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div class="stat-box" style="display: flex; justify-content: space-between; align-items: center; padding: 15px;">
                    <span>AI Mode</span>
                    <label class="switch">
                        <input type="checkbox" id="aiToggle" onchange="updateConfig('ai_enabled', this.checked)">
                        <span class="slider round"></span>
                    </label>
                </div>
                <div class="stat-box" style="display: flex; justify-content: space-between; align-items: center; padding: 15px;">
                    <span>Maintenance Mode</span>
                    <label class="switch">
                        <input type="checkbox" id="maintenanceToggle" onchange="updateConfig('maintenance_mode', this.checked)">
                        <span class="slider round"></span>
                    </label>
                </div>
            </div>
        </div>

        <!-- Terminal / Custom Command -->
        <div class="card">
            <h2><i class="fas fa-terminal"></i> Custom Command & Terminal History</h2>
            <div class="input-group">
                <input type="text" class="cmd-input" id="cmdInput" placeholder="Enter command (e.g. dir, ping google.com)..." onkeypress="handleKeyPress(event)">
                <div class="btn-group">
                    <button class="btn btn-action" onclick="runCommand()">
                        <i class="fas fa-play"></i> Run Command
                    </button>
                    <button class="btn btn-clear" onclick="clearOutput()">
                        <i class="fas fa-trash-alt"></i> Clear Output
                    </button>
                </div>
            </div>
            <div class="terminal" id="output">
                <div class="log-entry">Terminal ready. Waiting for input...</div>
            </div>
        </div>

        <!-- Real-time Bot History -->
        <div class="card">
            <h2><i class="fas fa-sync-alt"></i> Real-time Bot Logs (Server)</h2>
            <div class="terminal" id="realTimeLogs" style="background: #000; border-color: #444; max-height: 300px;">
                <div class="log-entry">Waiting for bot events...</div>
            </div>
        </div>

        <!-- Bot Management -->
        <div class="card">
            <h2><i class="fas fa-cog"></i> Bot Settings</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <p><strong>Bot ID:</strong> <code>@{{ bot_username }}</code></p>
                    <p><strong>Bot Token:</strong> <code style="background:#eee; padding:2px 5px; border-radius:4px;">{{ token_masked }}</code></p>
                    <p><strong>Owner ID:</strong> <code>{{ user_id }}</code></p>
                </div>
                <div class="btn-group" style="justify-content: flex-end;">
                    <button class="btn" style="background: #f39c12;" onclick="window.open('https://t.me/{{ bot_username }}', '_blank')">
                        <i class="fab fa-telegram-plane"></i> Open Bot
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function fetchLogs() {
            const terminal = document.getElementById("output");
            const entry = document.createElement("div");
            entry.className = "log-entry";
            entry.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span> <span class="log-cmd">> Fetching bot logs...</span><br><span class="log-res">Loading...</span>`;
            terminal.appendChild(entry);
            
            try {
                const response = await fetch("/api/logs");
                const data = await response.json();
                entry.querySelector(".log-res").textContent = data.logs || "No logs found.";
            } catch (e) {
                entry.querySelector(".log-res").textContent = "Error fetching logs: " + e.message;
            }
            terminal.scrollTop = terminal.scrollHeight;
        }

        async function controlBot(action) {
            if (!confirm(`Are you sure you want to ${action} the bot?`)) return;
            try {
                const response = await fetch("/api/bot/control", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({action: action})
                });
                const data = await response.json();
                alert(data.message || data.error);
                if (action === 'restart') location.reload();
            } catch (e) {
                alert("Error: " + e.message);
            }
        }

        async function updateActiveUsers() {
            try {
                const response = await fetch("/api/users");
                const data = await response.json();
                
                const container = document.getElementById("activeUsers");
                let usersHtml = "";
                
                if (data.users && data.users.length > 0) {
                    usersHtml += data.users.map(u => {
                        const statusColor = u.online ? "#00b894" : "#636e72";
                        const statusText = u.online ? "Online" : "Offline";
                        return `
                            <div class="user-badge" title="Last seen: ${new Date(u.last_seen * 1000).toLocaleTimeString()}">
                                <i class="fas fa-user-circle"></i>
                                <div style="display: flex; flex-direction: column; align-items: flex-start;">
                                    <span style="font-weight: bold;">@${u.username}</span>
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">ID: ${u.id}</span>
                                </div>
                                <span class="dot" style="margin-left: 10px; background-color: ${statusColor}; box-shadow: 0 0 5px ${statusColor};"></span>
                                <span style="font-size: 0.7rem; color: ${statusColor}; margin-left: 5px;">${statusText}</span>
                            </div>
                        `;
                    }).join("");
                }
                
                if (!usersHtml) {
                    container.innerHTML = '<p class="text-muted">No active users recorded.</p>';
                } else {
                    container.innerHTML = usersHtml;
                }
            } catch (e) {
                console.error("Failed to fetch users:", e);
            }
        }

        async function updateRemoteDevices() {
            try {
                const response = await fetch("/api/history"); // History API now includes remote_clients data
                const data = await response.json();
                const container = document.getElementById("remoteDevices");
                
                if (data.remote_clients && Object.keys(data.remote_clients).length > 0) {
                    container.innerHTML = Object.entries(data.remote_clients).map(([id, info]) => {
                        const lastSeen = new Date(info.last_seen * 1000).toLocaleTimeString();
                        const isOnline = (Date.now() / 1000) - info.last_seen < 60;
                        const statusColor = isOnline ? "#00b894" : "#d63031";
                        
                        return `
                            <div class="stat-box" style="text-align: left; position: relative;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <strong>Device: ${id}</strong>
                                    <span class="dot" style="background-color: ${statusColor}; box-shadow: 0 0 5px ${statusColor};"></span>
                                </div>
                                <div style="font-size: 0.85rem; color: var(--text-muted);">
                                    <div><i class="fas fa-clock"></i> Last Seen: ${lastSeen}</div>
                                    <div><i class="fas fa-list"></i> Pending: ${info.pending_commands.length} commands</div>
                                    <div><i class="fas fa-map-marker-alt"></i> Location: ${info.location.lat.toFixed(4)}, ${info.location.lon.toFixed(4)}</div>
                                </div>
                            </div>
                        `;
                    }).join("");
                } else {
                    container.innerHTML = '<p class="text-muted">No remote devices connected.</p>';
                }
            } catch (e) {
                console.error("Failed to fetch remote devices:", e);
            }
        }

        async function updateHistory() {
            try {
                const response = await fetch("/api/history");
                const data = await response.json();
                const container = document.getElementById("userHistory");
                if (data.history && data.history.length > 0) {
                    container.innerHTML = data.history.map(h => `
                        <div class="log-entry">
                            <span class="log-time">[${h.time}]</span> 
                            <span style="color: #a29bfe;">@${h.username} (${h.user_id})</span>: 
                            <span class="log-cmd">${h.command}</span>
                        </div>
                    `).reverse().join("");
                } else {
                    container.innerHTML = '<p class="text-muted">No command history yet.</p>';
                }
            } catch (e) {
                console.error("Failed to fetch history:", e);
            }
        }

        async function updateTasks() {
            try {
                const response = await fetch("/api/tasks");
                const data = await response.json();
                const container = document.getElementById("pendingTasks");
                if (data.tasks && data.tasks.length > 0) {
                    container.innerHTML = data.tasks.map(t => `
                        <div class="stat-box" style="text-align: left; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${t.task_name || 'Task'}</strong><br>
                                <small class="text-muted">User: ${t.user_id}</small>
                            </div>
                            <span class="user-badge" style="font-size: 0.8rem; background: #e3f2fd;">${t.status || 'Pending'}</span>
                        </div>
                    `).join("");
                } else {
                    container.innerHTML = '<p class="text-muted">No pending tasks.</p>';
                }
            } catch (e) {
                console.error("Failed to fetch tasks:", e);
            }
        }

        async function loadConfig() {
            try {
                const response = await fetch("/api/config");
                const data = await response.json();
                document.getElementById("aiToggle").checked = data.ai_enabled;
                document.getElementById("maintenanceToggle").checked = data.maintenance_mode;
            } catch (e) {
                console.error("Failed to fetch config:", e);
            }
        }

        async function updateConfig(key, value) {
            try {
                await fetch("/api/config", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({[key]: value})
                });
            } catch (e) {
                alert("Failed to update config: " + e.message);
            }
        }

        async function refreshStatus() {
            try {
                const response = await fetch("/api/status");
                const data = await response.json();
                if (data.status === "ok") {
                    document.getElementById("cpu").textContent = data.cpu + "%";
                    document.getElementById("ram").textContent = data.ram + "%";
                    document.getElementById("disk").textContent = data.disk + "%";
                    
                    // Fallback for old IDs if they exist
                    if(document.getElementById("cpu_val")) document.getElementById("cpu_val").textContent = data.cpu + "%";
                    if(document.getElementById("ram_val")) document.getElementById("ram_val").textContent = data.ram + "%";
                    if(document.getElementById("disk_val")) document.getElementById("disk_val").textContent = data.disk + "%";
                }
            } catch (e) {
                console.error("Failed to fetch status:", e);
                const errVal = "Err";
                if(document.getElementById("cpu")) document.getElementById("cpu").textContent = errVal;
                if(document.getElementById("ram")) document.getElementById("ram").textContent = errVal;
                if(document.getElementById("disk")) document.getElementById("disk").textContent = errVal;
            }
        }

        function handleKeyPress(e) {
            if (e.key === "Enter") runCommand();
        }

        async function runQuick(cmd) {
            document.getElementById("cmdInput").value = cmd;
            runCommand();
        }

        async function runCommand() {
            const cmdInput = document.getElementById("cmdInput");
            const cmd = cmdInput.value.trim();
            if (!cmd) return;
            
            const terminal = document.getElementById("output");
            const timestamp = new Date().toLocaleTimeString();
            
            // Add command to terminal
            const entry = document.createElement("div");
            entry.className = "log-entry";
            entry.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="log-cmd">> ${cmd}</span><br><span class="log-res">Running...</span>`;
            terminal.appendChild(entry);
            terminal.scrollTop = terminal.scrollHeight;
            
            // Also handle old output style if it exists
            const oldOutput = document.getElementById("output_text");
            if(oldOutput) oldOutput.textContent = "Running: " + cmd + "...";
            
            try {
                const response = await fetch("/api/execute", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({command: cmd})
                });
                const data = await response.json();
                
                const resContent = data.output || data.error || "Execution completed (no output).";
                const resSpan = entry.querySelector(".log-res");
                resSpan.textContent = resContent;
                
                if(oldOutput) oldOutput.textContent = resContent;
            } catch (e) {
                const resSpan = entry.querySelector(".log-res");
                resSpan.style.color = "#ff7675";
                resSpan.textContent = "Error: " + e.message;
                if(oldOutput) oldOutput.textContent = "Error: " + e.message;
            }
            
            cmdInput.value = "";
            terminal.scrollTop = terminal.scrollHeight;
        }

        function clearOutput() {
            document.getElementById("output").innerHTML = '<div class="log-entry">Terminal cleared.</div>';
        }

        async function fetchLogs() {
            try {
                const response = await fetch("/api/logs");
                const data = await response.json();
                const container = document.getElementById("realTimeLogs");
                if (data.logs) {
                    container.innerHTML = data.logs.split("\n").map(line => `
                        <div class="log-entry">
                            <span class="log-res">${line}</span>
                        </div>
                    `).reverse().join("");
                }
            } catch (e) {
                console.error("Failed to fetch logs:", e);
            }
        }

        // Auto-refresh logic
        setInterval(refreshStatus, 5000);
        setInterval(updateActiveUsers, 10000);
        setInterval(updateRemoteDevices, 5000);
        setInterval(updateHistory, 5000);
        setInterval(updateTasks, 10000);
        setInterval(fetchLogs, 3000);
        
        // Initial load
        refreshStatus();
        updateActiveUsers();
        updateRemoteDevices();
        updateHistory();
        updateTasks();
        fetchLogs();
        loadConfig();
    </script>
</body>
</html>
'''

@app.route("/")
def index():
    token_masked = TOKEN[:10] + "..." + TOKEN[-5:] if TOKEN and len(TOKEN) > 15 else "Not set"
    bot_username = "alberteinstein247_bot" # Fallback
    if bot_app and bot_app.bot:
        try:
            # We can't easily await here since it's a Flask route, 
            # but we can store it during bot startup or use a known value.
            # For now, we'll use the one from the prompt/logs.
            pass 
        except: pass
        
    return render_template_string(
        HTML_TEMPLATE,
        port=WEB_PORT,
        user_id=ALLOWED_USER_ID or "Not set",
        token_masked=token_masked,
        bot_username=bot_username
    )

@app.route("/overview")
def overview():
    return index()

@app.route("/api/status")
def api_status():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        return jsonify({
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "status": "ok"
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"})

@app.route("/api/execute", methods=["POST"])
def api_execute():
    try:
        data = request.get_json()
        command = data.get("command", "")
        
        if not command:
            return jsonify({"error": "No command provided"})
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd="d:/clow bot",
            timeout=30
        )
        
        output = result.stdout if result.stdout else result.stderr
        if not output:
            output = "Command executed with no output."
            
        return jsonify({
            "command": command,
            "output": output,
            "status": "success",
            "returncode": result.returncode
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"})

# ============== REMOTE CLIENT API ==============

@app.route("/api/phone/poll/<user_id>", methods=["GET"])
def phone_poll(user_id):
    """Endpoint for user's phone to poll for commands"""
    if user_id not in remote_clients:
        remote_clients[user_id] = {"last_seen": time.time(), "pending_commands": [], "location": {"lat": 0, "lon": 0}}
    
    remote_clients[user_id]["last_seen"] = time.time()
    commands = remote_clients[user_id].get("pending_commands", [])
    
    if commands:
        add_to_logs(f"Phone {user_id} polled and received: {commands}")
        # Clear after polling to prevent repeated execution
        remote_clients[user_id]["pending_commands"] = []
    
    return jsonify({"commands": commands, "status": "ok", "timestamp": time.time()})

@app.route("/api/phone/report/<user_id>", methods=["POST"])
def phone_report(user_id):
    """Endpoint for phone to report results (battery, location, photo, etc.)"""
    try:
        data = request.get_json()
        action = data.get("action")
        result = data.get("result")
        
        # Update remote client state
        if user_id not in remote_clients:
            remote_clients[user_id] = {"last_seen": time.time(), "pending_commands": [], "location": {"lat": 0, "lon": 0}}
        
        remote_clients[user_id]["last_seen"] = time.time()
        
        # Handle specific report types
        if action == "location" and isinstance(result, dict):
            lat = result.get("lat")
            lon = result.get("lon")
            remote_clients[user_id]["location"] = {"lat": lat, "lon": lon}
            
            # Real-time sharing with other users
            if user_id in share_location_active:
                for target_chat_id in share_location_active[user_id]:
                    # We need a way to send this to Telegram. 
                    # Since this is a Flask route, we use the global bot_app
                    if bot_app:
                        asyncio.run_coroutine_threadsafe(
                            bot_app.bot.send_location(chat_id=target_chat_id, latitude=lat, longitude=lon),
                            bot_app.loop
                        )
        
        add_to_logs(f"Remote Phone ({user_id}) reported {action}")
        return jsonify({"status": "received"})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"})

@app.route("/api/logs")
def api_logs():
    return jsonify({"logs": "\n".join(bot_logs)})

@app.route("/api/users")
def api_users():
    users_data = []
    current_time = time.time()
    for uid, info in active_users_set.items():
        is_online = (current_time - info["last_seen"]) < 300 # 5 minutes
        users_data.append({
            "id": uid,
            "username": info["username"],
            "last_seen": info["last_seen"],
            "online": is_online
        })
    return jsonify({"users": users_data})

@app.route("/api/history")
def api_history():
    return jsonify({
        "history": user_commands_history,
        "remote_clients": remote_clients
    })

@app.route("/api/tasks")
def api_tasks():
    try:
        tasks = []
        if os.path.exists("pending_tasks.json"):
            with open("pending_tasks.json", "r") as f:
                tasks = json.load(f)
        
        # Add remote commands as tasks for dashboard visibility
        for uid, data in remote_clients.items():
            for cmd in data.get("pending_commands", []):
                tasks.append({
                    "task_name": f"Remote: {cmd}",
                    "user_id": uid,
                    "status": "Queued",
                    "priority": "High"
                })
        return jsonify({"tasks": tasks})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    global bot_config
    if request.method == "POST":
        data = request.get_json()
        bot_config.update(data)
        add_to_logs(f"Bot config updated: {data}")
        return jsonify({"status": "ok", "config": bot_config})
    return jsonify(bot_config)

@app.route("/api/tunnel", methods=["GET", "POST"])
def api_tunnel():
    global cf_tunnel_process, cf_tunnel_url
    if request.method == "POST":
        data = request.get_json()
        action = data.get("action")
        
        if action == "start":
            if cf_tunnel_process:
                return jsonify({"status": "error", "message": "Tunnel already running", "url": cf_tunnel_url})
            
            try:
                # Start cloudflared tunnel
                # Use --url to specify localhost and port
                cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{WEB_PORT}"]
                cf_tunnel_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                
                # Start a thread to parse the URL from output
                def track_url(process):
                    global cf_tunnel_url
                    import re
                    try:
                        for line in process.stdout:
                            add_to_logs(f"Cloudflared: {line.strip()}")
                            if ".trycloudflare.com" in line:
                                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                                if match:
                                    cf_tunnel_url = match.group(0)
                                    add_to_logs(f"Cloudflare Tunnel Live: {cf_tunnel_url}")
                                    break
                    except Exception as e:
                        add_to_logs(f"Tunnel tracking error: {e}")

                import threading
                threading.Thread(target=track_url, args=(cf_tunnel_process,), daemon=True).start()
                
                return jsonify({"status": "ok", "message": "Tunnel initiated", "url": "Starting..."})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})
                
        elif action == "stop":
            if cf_tunnel_process:
                cf_tunnel_process.terminate()
                cf_tunnel_process = None
                cf_tunnel_url = None
                return jsonify({"status": "ok", "message": "Tunnel stopped"})
            return jsonify({"status": "error", "message": "No tunnel running"})
            
    return jsonify({"status": "ok", "url": cf_tunnel_url, "running": cf_tunnel_process is not None})

@app.route("/api/bot/control", methods=["POST"])
def api_bot_control():
    try:
        data = request.get_json()
        action = data.get("action")
        if action == "restart":
            add_to_logs("Restarting bot via dashboard...")
            # Simple restart: exit and let the process manager/script restart it
            # Or just clear state. For a real restart, we'd need a wrapper script.
            os._exit(0) 
        return jsonify({"message": f"Action {action} initiated"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/files")
def api_files():
    try:
        files = os.listdir("d:/clow bot")
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)})

# Discord Client for Reading/Auto-reply
discord_client = None

async def start_discord_bot():
    global discord_client
    if not DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN == "your_discord_bot_token_here":
        add_to_logs("Discord Bot Token not set. Auto-reply disabled.")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    discord_client = discord_commands.Bot(command_prefix="!", intents=intents)

    @discord_client.event
    async def on_ready():
        add_to_logs(f"Discord Bot connected as {discord_client.user}")
        print(f"✅ Discord Bot logged in as {discord_client.user}")
        # Send a test message to a channel to verify it's working
        for guild in discord_client.guilds:
            for channel in guild.text_channels:
                try:
                    await channel.send("👨‍🔬 **Einstein System Initialized.** System is now monitoring this sector for transmissions.")
                    print(f"DEBUG: Sent startup message to {channel.name} in {guild.name}")
                    break # Just one channel per guild
                except:
                    continue

    @discord_client.event
    async def on_message(message):
        print(f"DEBUG: Discord message received from {message.author}: {message.content}")
        # Explicitly log to bot dashboard logs for visibility
        add_to_logs(f"Discord Event: Message from {message.author} in {message.channel}")
        
        if message.author == discord_client.user:
            return

        # Einstein "Instant" Response logic
        try:
            # Process command if any (like !help)
            await discord_client.process_commands(message)
            
            async with message.channel.typing():
                reply_text = f"👨‍🔬 *Einstein here.* Analyzing your transmission in {message.channel}: '{message.content}'..."
                
                try:
                    # Use a slightly faster prompt for "instant" feel
                    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
                    resp = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": ollama_model,
                            "prompt": f"Act as Albert Einstein. A student said '{message.content}' in the {message.channel} channel. Give a very short, brilliant, and instant reply.",
                            "stream": False
                        },
                        timeout=5
                    )
                    if resp.status_code == 200:
                        reply_text = resp.json().get('response', reply_text)
                except Exception as ai_err:
                    print(f"DEBUG: AI Response error: {ai_err}")
                    add_to_logs(f"AI Error: {ai_err}")
                    
                await message.reply(reply_text)
                print(f"DEBUG: Reply sent to {message.author}")
        except Exception as msg_err:
            print(f"DEBUG: Error sending Discord reply: {msg_err}")
            add_to_logs(f"Discord Reply Error: {msg_err}")

    try:
        await discord_client.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        add_to_logs(f"Discord Bot Error: {e}")

def run_flask():
    print(f"Web server starting on http://127.0.0.1:{WEB_PORT}")
    app.run(host="127.0.0.1", port=WEB_PORT, debug=False, use_reloader=False)

def run_bot():
    global bot_app
    
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        return
        
    bot_app = ApplicationBuilder().token(TOKEN).read_timeout(60).write_timeout(60).connect_timeout(60).pool_timeout(60).build()
    
    # Basic commands
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    
    # Multi-task commands
    bot_app.add_handler(CommandHandler("weather", lambda u, c: get_weather(u, " ".join(c.args) if c.args else None)))
    bot_app.add_handler(CommandHandler("search", lambda u, c: search_web(u, " ".join(c.args) if c.args else None)))
    bot_app.add_handler(CommandHandler("ai", lambda u, c: ai_chat(u, " ".join(c.args) if c.args else None)))
    bot_app.add_handler(CommandHandler("facebook", lambda u, c: facebook_control(u, None)))
    bot_app.add_handler(CommandHandler("fb", lambda u, c: facebook_control(u, None)))
    bot_app.add_handler(CommandHandler("youtube", lambda u, c: youtube_control(u, None)))
    bot_app.add_handler(CommandHandler("tiktok", lambda u, c: tiktok_control(u, None)))
    bot_app.add_handler(CommandHandler("tt", lambda u, c: tiktok_control(u, None)))
    
    # OpenClaw features - Browser & Screenshot
    bot_app.add_handler(CommandHandler("browser", browser_control))
    bot_app.add_handler(CommandHandler("screenshot", take_screenshot))
    
    # OpenClaw features - GitHub
    bot_app.add_handler(CommandHandler("github", github_control))
    bot_app.add_handler(CommandHandler("git", github_control))
    
    # OpenClaw features - Twitter/X
    bot_app.add_handler(CommandHandler("twitter", twitter_control))
    bot_app.add_handler(CommandHandler("tweet", twitter_control))
    bot_app.add_handler(CommandHandler("x", twitter_control))
    
    # OpenClaw features - Gmail
    bot_app.add_handler(CommandHandler("gmail", gmail_control))
    bot_app.add_handler(CommandHandler("email", gmail_control))
    
    # OpenClaw features - Spotify
    bot_app.add_handler(CommandHandler("spotify", spotify_control))
    bot_app.add_handler(CommandHandler("music", spotify_control))
    
    # OpenClaw features - Notes (Obsidian-like)
    bot_app.add_handler(CommandHandler("note", notes_manager))
    bot_app.add_handler(CommandHandler("notes", notes_manager))
    
    # Core Handlers
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", show_help))
    bot_app.add_handler(CommandHandler("stop", stop_all_actions))
    bot_app.add_handler(CommandHandler("clear", clear_chat))
    bot_app.add_handler(CommandHandler("files", list_workspace_files))
    
    # Cloudflare Tunnel Command
    bot_app.add_handler(CommandHandler("tunnel", tunnel_control))
    
    # OpenClaw features - Utilities
    bot_app.add_handler(CommandHandler("utils", utilities_manager))
    bot_app.add_handler(CommandHandler("util", utilities_manager))
    bot_app.add_handler(CommandHandler("tools", utilities_manager))
    
    # New Utility Features - Calculator
    bot_app.add_handler(CommandHandler("calc", calculator))
    bot_app.add_handler(CommandHandler("calculate", calculator))
    
    # New Utility Features - Fun & Games
    bot_app.add_handler(CommandHandler("joke", random_joke))
    bot_app.add_handler(CommandHandler("quote", random_quote))
    bot_app.add_handler(CommandHandler("fact", random_facts))
    bot_app.add_handler(CommandHandler("dice", roll_dice))
    bot_app.add_handler(CommandHandler("coin", flip_coin))
    
    # New Utility Features - Info & Search
    bot_app.add_handler(CommandHandler("time", world_time))
    bot_app.add_handler(CommandHandler("ip", ip_lookup))
    bot_app.add_handler(CommandHandler("wiki", wikipedia_search))
    
    # New Utility Features - Text Tools
    bot_app.add_handler(CommandHandler("translate", translate_reply))
    bot_app.add_handler(CommandHandler("tr", translate_reply))
    bot_app.add_handler(CommandHandler("translate_text", translate_text))
    bot_app.add_handler(CommandHandler("timer", set_timer))
    bot_app.add_handler(CommandHandler("convert", unit_converter))
    bot_app.add_handler(CommandHandler("format", text_formatter))
    
    # Video Downloader - Universal (YouTube, Facebook, TikTok, Instagram, etc.)
    bot_app.add_handler(CommandHandler("video", video_downloader))
    bot_app.add_handler(CommandHandler("video_hq", video_downloader))
    bot_app.add_handler(CommandHandler("dl", video_downloader))
    bot_app.add_handler(CommandHandler("download", video_downloader))
    bot_app.add_handler(CommandHandler("continue", continue_tasks))
    
    # Video Streaming - Play without downloading
    bot_app.add_handler(CommandHandler("play", play_video))
    bot_app.add_handler(CommandHandler("stream", play_video))
    
    # YouTube Command
    bot_app.add_handler(CommandHandler("yt", youtube_command))
    bot_app.add_handler(CommandHandler("music", music_downloader))
    
    # Phone Command
    bot_app.add_handler(CommandHandler("phone", phone_control))
    
    # OpenClaw features - Discord & Slack
    bot_app.add_handler(CommandHandler("discord", discord_webhook))
    bot_app.add_handler(CommandHandler("slack", slack_webhook))
    
    # OpenClaw features - AI Smart Command Processor
    bot_app.add_handler(CommandHandler("smart", ai_command_processor))
    bot_app.add_handler(CommandHandler("auto", ai_command_processor))
    
    # Facebook Handler
    bot_app.add_handler(CommandHandler("facebook", facebook_control))
    
    # AI Generation
    bot_app.add_handler(CommandHandler("vgen", ai_video_generator))
    bot_app.add_handler(CommandHandler("thumb", ai_thumbnail_generator))
    bot_app.add_handler(CommandHandler("thumbnail", ai_thumbnail_generator))
    bot_app.add_handler(CommandHandler("fb", facebook_control))
    bot_app.add_handler(CommandHandler("fb_post", lambda u, c: facebook_control(u, action="post")))
    bot_app.add_handler(CommandHandler("fb_stats", lambda u, c: facebook_control(u, action="stats")))
    
    # OpenClaw features - Calendar & Travel
    bot_app.add_handler(CommandHandler("calendar", calendar_manager))
    bot_app.add_handler(CommandHandler("cal", calendar_manager))
    bot_app.add_handler(CommandHandler("flight", flight_checkin))
    bot_app.add_handler(CommandHandler("travel", flight_checkin))
    
    # OpenClaw features - File Manager
    bot_app.add_handler(CommandHandler("file", file_manager))
    bot_app.add_handler(CommandHandler("files", file_manager))
    
    # OpenClaw features - WhatsApp
    bot_app.add_handler(CommandHandler("whatsapp", whatsapp_control))
    bot_app.add_handler(CommandHandler("wa", whatsapp_control))
    
    # OpenClaw features - Claude AI
    # bot_app.add_handler(CommandHandler("claude", claude_ai)) # Commented out if not fully implemented
    
    # OpenClaw features - Ollama Local AI
    bot_app.add_handler(CommandHandler("ollama", ollama_chat))
    bot_app.add_handler(CommandHandler("local", ollama_chat))
    
    # Bot Profile Management
    bot_app.add_handler(CommandHandler("botprofile", bot_profile))
    bot_app.add_handler(CommandHandler("profile", bot_profile))
    
    # Video Downloaders
    bot_app.add_handler(CommandHandler("multivideo", multi_video_downloader))
    bot_app.add_handler(CommandHandler("multi", multi_video_downloader))
    
    # AI Generation
    # bot_app.add_handler(CommandHandler("vgen", ai_video_generator)) # Avoid duplicate registration
    bot_app.add_handler(CommandHandler("gen", generate_image))
    bot_app.add_handler(CommandHandler("gif", video_to_gif))
    bot_app.add_handler(CommandHandler("playlist", youtube_playlist_dl))
    
    # Language Selection
    bot_app.add_handler(CommandHandler("language", language_command))
    bot_app.add_handler(CommandHandler("lang", language_command))
    
    # Document/file upload handler
    bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Callback handler for inline buttons
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Message handler
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_media))
    bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_media))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("=" * 50)
    print("Bot is starting...")
    print(f"Web Control Panel: http://127.0.0.1:{WEB_PORT}")
    print(f"Alternative URL: http://127.0.0.1:{WEB_PORT}/overview")
    print("=" * 50)
    
    bot_app.run_polling()

def run_discord_bot_process():
    """Wrapper function for multiprocessing to run Discord bot"""
    import asyncio
    asyncio.run(start_discord_bot())

if __name__ == '__main__':
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
    else:
        # Start background cleanup thread
        cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
        cleanup_thread.start()
        
        # Start Flask web server in a thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Start Discord bot in a separate process
        from multiprocessing import Process
        discord_process = Process(target=run_discord_bot_process, daemon=True)
        discord_process.start()
        
        # Run Telegram bot
        run_bot()
