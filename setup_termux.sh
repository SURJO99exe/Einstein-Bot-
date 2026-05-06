#!/data/data/com.termux/files/usr/bin/bash

# Einstein Bot Termux Setup Script
# Created for mobile compatibility

echo "🚀 Initializing Termux environment for Einstein Bot..."

# Update packages
pkg update -y && pkg upgrade -y

# Install core dependencies
pkg install python python-pip git ffmpeg libjpeg-turbo -y

# Install build dependencies for some python packages
pkg install clang make binutils -y

# Fix for some native extensions
export LDFLAGS="-L${PREFIX}/lib"
export CPPFLAGS="-I${PREFIX}/include"

# Install python requirements
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Additional Termux-specific handling for voice
# Note: gTTS works fine, but PyNaCl might need manual compilation on some devices
# If PyNaCl fails, we skip voice for now to keep it running

echo "✅ Setup Complete!"
echo "💡 To run the bot, use: python bot.py"
