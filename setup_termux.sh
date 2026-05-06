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

# Create essential folders
echo "� Creating essential bot folders..."
mkdir -p downloads uploads assets media_analysis notes screenshots temp_tts

# Set up virtual environment
if [ ! -d "venv" ]; then
    echo "🌐 Creating virtual environment (venv)..."
    python -m venv venv
else
    echo "✅ Virtual environment already exists."
fi

# Activate venv and install requirements
echo "📦 Installing Python dependencies inside venv..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup Complete!"
echo "💡 To run the bot in the future, use:"
echo "   source venv/bin/activate"
echo "   python bot.py"
