def detect_language(text):
    """Simple language detection based on character sets or keywords"""
    # Placeholder for actual detection logic
    if any(ord(c) > 127 for c in text): # Very basic check for non-ASCII
        return 'bn' # Default to Bengali for non-ASCII in this context
    return 'en'

def get_text(key, lang='en', **kwargs):
    """Retrieve localized text for a given key and language"""
    texts = {
        'en': {
            'welcome': "🧠 <b>Einstein OS - Laboratory Ready</b>\n━━━━━━━━━━━━━━━━━━━━━\nWelcome to the laboratory. Use /help for a full manual of scientific commands.\n\n🌐 <b>Web Interface:</b> {web_port}",
            'system_status': "📊 <b>System Status</b>\n━━━━━━━━━━━━━━━━━━━━━\n🧠 <b>CPU:</b> {cpu}%\n📟 <b>RAM:</b> {ram}%\n💾 <b>Disk:</b> {disk}%",
            'weather_usage': "🌤️ <b>Weather Monitor</b>\nUsage: <code>/weather [city]</code>",
            'thinking': "Analyzing quantum data...",
            'help_title': "Einstein OS Command Manual"
        },
        'bn': {
            'welcome': "🧠 <b>আইনস্টাইন ওএস - গবেষণাগার প্রস্তুত</b>\n━━━━━━━━━━━━━━━━━━━━━\nগবেষণাগারে স্বাগতম। বৈজ্ঞানিক কমান্ডের সম্পূর্ণ ম্যানুয়ালের জন্য /help ব্যবহার করুন।\n\n🌐 <b>ওয়েব ইন্টারফেস:</b> {web_port}",
            'system_status': "📊 <b>সিস্টেম স্ট্যাটাস</b>\n━━━━━━━━━━━━━━━━━━━━━\n🧠 <b>সিপিইউ:</b> {cpu}%\n📟 <b>র‍্যাম:</b> {ram}%\n💾 <b>ডিস্ক:</b> {disk}%",
            'weather_usage': "🌤️ <b>আবহাওয়া মনিটর</b>\nব্যবহার: <code>/weather [শহর]</code>",
            'thinking': "কোয়ান্টাম তথ্য বিশ্লেষণ করা হচ্ছে...",
            'help_title': "আইনস্টাইন ওএস কমান্ড ম্যানুয়াল"
        }
    }
    
    lang_texts = texts.get(lang, texts['en'])
    text = lang_texts.get(key, texts['en'].get(key, key))
    return text.format(**kwargs)

def get_language_name(lang_code):
    """Get the full name of a language from its code"""
    names = {
        'en': 'English',
        'bn': 'Bengali',
        'hi': 'Hindi',
        'es': 'Spanish',
        'ar': 'Arabic',
        'zh': 'Chinese'
    }
    return names.get(lang_code, lang_code)

LANGUAGES = ['en', 'bn', 'hi', 'es', 'ar', 'zh']
