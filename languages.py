"""
Multi-language support for OpenClowd Bot
Supports: English, Bengali (αª¼αª╛αªéαª▓αª╛), Hindi (αñ╣αñ┐αñ¿αÑìαñªαÑÇ), Spanish, French, Arabic, Chinese
"""

LANGUAGES = {
    'en': {
        'welcome': "≡ƒæï Welcome to OpenClowd Bot!\n\nI am Albert Einstein, your AI assistant.\n≡ƒîÉ Web Control: {web_port}",
        'thinking': "≡ƒñû Thinking...",
        'error': "Γ¥î Error: {error}",
        'access_denied': "Γ¥î Access Denied!\nYour ID: {user_id}\nAdd this to .env file as ALLOWED_USER_ID",
        'system_status': "≡ƒôè **System Status**\n≡ƒûÑ CPU: {cpu}%\n≡ƒÆ╛ RAM: {ram}%\n≡ƒÆ╜ Disk: {disk}%",
        'help_title': "≡ƒôû **OpenClowd Bot - Complete Commands:**",
        'ai_thinking': "≡ƒªÖ Ollama ({model}) is thinking...",
        'ai_response': "≡ƒªÖ {response}",
        'cmd_active': "≡ƒÆ╗ CMD Mode Active!\nSend any command to run in terminal.",
        'weather_usage': "≡ƒîñ∩╕Å Weather Info\n\nUsage: /weather [city name]\nExample: /weather Dhaka",
        'search_usage': "≡ƒöì Web Search\n\nUsage: /search [your query]\nExample: /search latest tech news",
        'ollama_mode': "≡ƒªÖ Ollama Local AI Mode!\n\nFree local AI - No API key needed!\n\nJust type any message and I'll reply with AI!",
        'botprofile_help': "≡ƒñû **Bot Profile Manager**\n\n**Usage:**\n/botprofile name [new_name]\n/botprofile description [text]\n/botprofile about [text]\n/botprofile photo\n/botprofile info",
    },
    'bn': {
        'welcome': "≡ƒæï αªôαª¬αºçαª¿αªòαºìαª▓αª╛αªëαªí αª¼αªƒαºç αª╕αºìαª¼αª╛αªùαªñαª«!\n\nαªåαª«αª┐ αªåαª▓αª¼αª╛αª░αºìαªƒ αªåαªçαª¿αª╕αºìαªƒαª╛αªçαª¿, αªåαª¬αª¿αª╛αª░ AI αª╕αª╣αªòαª╛αª░αºÇαÑñ\n≡ƒîÉ αªôαª»αª╝αºçαª¼ αªòαª¿αºìαªƒαºìαª░αºïαª▓: {web_port}",
        'thinking': "≡ƒñû αª¡αª╛αª¼αª¢αª┐...",
        'error': "Γ¥î αªñαºìαª░αºüαªƒαª┐: {error}",
        'access_denied': "Γ¥î αªàαºìαª»αª╛αªòαºìαª╕αºçαª╕ αª¿αª┐αª╖αª┐αªªαºìαªº!\nαªåαª¬αª¿αª╛αª░ αªåαªçαªíαª┐: {user_id}\n.ENV αª½αª╛αªçαª▓αºç ALLOWED_USER_ID αª╣αª┐αª╕αºçαª¼αºç αª»αºïαªù αªòαª░αºüαª¿",
        'system_status': "≡ƒôè **αª╕αª┐αª╕αºìαªƒαºçαª« αª╕αºìαªƒαºìαª»αª╛αªƒαª╛αª╕**\n≡ƒûÑ CPU: {cpu}%\n≡ƒÆ╛ RAM: {ram}%\n≡ƒÆ╜ Disk: {disk}%",
        'help_title': "≡ƒôû **αªôαª¬αºçαª¿αªòαºìαª▓αª╛αªëαªí αª¼αªƒ - αª╕αª«αºìαª¬αºéαª░αºìαªú αªòαª«αª╛αª¿αºìαªí:**",
        'ai_thinking': "≡ƒªÖ αªôαª▓αºìαª▓αª╛αª«αª╛ ({model}) αª¡αª╛αª¼αª¢αºç...",
        'ai_response': "≡ƒªÖ {response}",
        'cmd_active': "≡ƒÆ╗ CMD αª«αºïαªí αª╕αªòαºìαª░αª┐αª»αª╝!\nαªƒαª╛αª░αºìαª«αª┐αª¿αª╛αª▓αºç αªÜαª╛αª▓αª╛αª¿αºïαª░ αª£αª¿αºìαª» αª»αºçαªòαºïαª¿αºï αªòαª«αª╛αª¿αºìαªí αª¬αª╛αªáαª╛αª¿αÑñ",
        'weather_usage': "≡ƒîñ∩╕Å αªåαª¼αª╣αª╛αªôαª»αª╝αª╛ αªñαªÑαºìαª»\n\nαª¼αºìαª»αª¼αª╣αª╛αª░: /weather [αª╢αª╣αª░αºçαª░ αª¿αª╛αª«]\nαªëαªªαª╛αª╣αª░αªú: /weather αªóαª╛αªòαª╛",
        'search_usage': "≡ƒöì αªôαª»αª╝αºçαª¼ αª╕αª╛αª░αºìαªÜ\n\nαª¼αºìαª»αª¼αª╣αª╛αª░: /search [αªåαª¬αª¿αª╛αª░ αª¬αºìαª░αª╢αºìαª¿]\nαªëαªªαª╛αª╣αª░αªú: /search latest tech news",
        'ollama_mode': "≡ƒªÖ αªôαª▓αºìαª▓αª╛αª«αª╛ αª▓αºïαªòαª╛αª▓ AI αª«αºïαªí!\n\nαª½αºìαª░αª┐ αª▓αºïαªòαª╛αª▓ AI - αªòαºïαª¿ API αªòαºÇ αª▓αª╛αªùαª¼αºç αª¿αª╛!\n\nαª»αºçαªòαºïαª¿αºï αª«αºçαª╕αºçαª£ αªƒαª╛αªçαª¬ αªòαª░αºüαª¿ αªÅαª¼αªé AI αª░αª┐αª¬αºìαª▓αª╛αªç αª¬αª╛αª¼αºçαª¿!",
        'botprofile_help': "≡ƒñû **αª¼αªƒ αª¬αºìαª░αºïαª½αª╛αªçαª▓ αª«αºìαª»αª╛αª¿αºçαª£αª╛αª░**\n\n**αª¼αºìαª»αª¼αª╣αª╛αª░:**\n/botprofile name [αª¿αªñαºüαª¿_αª¿αª╛αª«]\n/botprofile description [αªƒαºçαªòαºìαª╕αªƒ]\n/botprofile about [αªƒαºçαªòαºìαª╕αªƒ]\n/botprofile photo\n/botprofile info",
    },
    'hi': {
        'welcome': "≡ƒæô αñôαñ¬αñ¿αñòαÑìαñ▓αñ╛αñëαñí αñ¼αÑëαñƒ αñ«αÑçαñé αñåαñ¬αñòαñ╛ αñ╕αÑìαñ╡αñ╛αñùαññ αñ╣αÑê!\n\nαñ«αÑêαñé αñàαñ▓αÑìαñ¼αñ░αÑìαñƒ αñåαñçαñéαñ╕αÑìαñƒαÑÇαñ¿, αñåαñ¬αñòαñ╛ AI αñ╕αñ╣αñ╛αñ»αñò αñ╣αÑéαñéαÑñ\n≡ƒîÉ αñ╡αÑçαñ¼ αñ¿αñ┐αñ»αñéαññαÑìαñ░αñú: {web_port}",
        'thinking': "≡ƒñû αñ╕αÑïαñÜ αñ░αñ╣αñ╛ αñ╣αÑéαñé...",
        'error': "Γ¥î αññαÑìαñ░αÑüαñƒαñ┐: {error}",
        'access_denied': "Γ¥î αñ¬αñ╣αÑüαñéαñÜ αñ¿αñ┐αñ╖αÑçαñº!\nαñåαñ¬αñòαÑÇ αñåαñêαñíαÑÇ: {user_id}\n.ENV αñ½αñ╛αñçαñ▓ αñ«αÑçαñé ALLOWED_USER_ID αñòαÑç αñ░αÑéαñ¬ αñ«αÑçαñé αñ£αÑïαñíαñ╝αÑçαñé",
        'system_status': "≡ƒôè **αñ╕αñ┐αñ╕αÑìαñƒαñ« αñ╕αÑìαñÑαñ┐αññαñ┐**\n≡ƒûÑ CPU: {cpu}%\n≡ƒÆ╛ RAM: {ram}%\n≡ƒÆ╜ Disk: {disk}%",
        'help_title': "≡ƒôû **αñôαñ¬αñ¿αñòαÑìαñ▓αñ╛αñëαñí αñ¼αÑëαñƒ - αñ¬αÑéαñ░αÑìαñú αñòαñ«αñ╛αñéαñí:**",
        'ai_thinking': "≡ƒªÖ αñôαñ▓αñ╛αñ«αñ╛ ({model}) αñ╕αÑïαñÜ αñ░αñ╣αñ╛ αñ╣αÑê...",
        'ai_response': "≡ƒªÖ {response}",
        'cmd_active': "≡ƒÆ╗ CMD αñ«αÑïαñí αñ╕αñòαÑìαñ░αñ┐αñ»!\nαñƒαñ░αÑìαñ«αñ┐αñ¿αñ▓ αñ«αÑçαñé αñÜαñ▓αñ╛αñ¿αÑç αñòαÑç αñ▓αñ┐αñÅ αñòαÑïαñê αñ¡αÑÇ αñòαñ«αñ╛αñéαñí αñ¡αÑçαñ£αÑçαñéαÑñ",
        'weather_usage': "≡ƒîñ∩╕Å αñ«αÑîαñ╕αñ« αñ£αñ╛αñ¿αñòαñ╛αñ░αÑÇ\n\nαñëαñ¬αñ»αÑïαñù: /weather [αñ╢αñ╣αñ░ αñòαñ╛ αñ¿αñ╛αñ«]\nαñëαñªαñ╛αñ╣αñ░αñú: /weather αñªαñ┐αñ▓αÑìαñ▓αÑÇ",
        'search_usage': "≡ƒöì αñ╡αÑçαñ¼ αñûαÑïαñ£\n\nαñëαñ¬αñ»αÑïαñù: /search [αñåαñ¬αñòαñ╛ αñ¬αÑìαñ░αñ╢αÑìαñ¿]\nαñëαñªαñ╛αñ╣αñ░αñú: /search latest tech news",
        'ollama_mode': "≡ƒªÖ αñôαñ▓αñ╛αñ«αñ╛ αñ▓αÑïαñòαñ▓ AI αñ«αÑïαñí!\n\nαñ½αÑìαñ░αÑÇ αñ▓αÑïαñòαñ▓ AI - αñòαÑïαñê API αñòαÑÇ αñ£αñ░αÑéαñ░αññ αñ¿αñ╣αÑÇαñé!\n\nαñòαÑïαñê αñ¡αÑÇ αñ«αÑêαñ╕αÑçαñ£ αñƒαñ╛αñçαñ¬ αñòαñ░αÑçαñé αñöαñ░ AI αñ£αñ╡αñ╛αñ¼ αñ¬αñ╛αñÅαñé!",
        'botprofile_help': "≡ƒñû **αñ¼αÑëαñƒ αñ¬αÑìαñ░αÑïαñ½αñ╛αñçαñ▓ αñ«αÑêαñ¿αÑçαñ£αñ░**\n\n**αñëαñ¬αñ»αÑïαñù:**\n/botprofile name [αñ¿αñ»αñ╛_αñ¿αñ╛αñ«]\n/botprofile description [αñƒαÑçαñòαÑìαñ╕αÑìαñƒ]\n/botprofile about [αñƒαÑçαñòαÑìαñ╕αÑìαñƒ]\n/botprofile photo\n/botprofile info",
    },
    'es': {
        'welcome': "≡ƒæï ┬íBienvenido a OpenClowd Bot!\n\nSoy Albert Einstein, tu asistente de IA.\n≡ƒîÉ Control Web: {web_port}",
        'thinking': "≡ƒñû Pensando...",
        'error': "Γ¥î Error: {error}",
        'access_denied': "Γ¥î ┬íAcceso Denegado!\nTu ID: {user_id}\nAgrega esto al archivo .env como ALLOWED_USER_ID",
        'system_status': "≡ƒôè **Estado del Sistema**\n≡ƒûÑ CPU: {cpu}%\n≡ƒÆ╛ RAM: {ram}%\n≡ƒÆ╜ Disk: {disk}%",
        'help_title': "≡ƒôû **OpenClowd Bot - Comandos Completos:**",
        'ai_thinking': "≡ƒªÖ Ollama ({model}) est├í pensando...",
        'ai_response': "≡ƒªÖ {response}",
        'cmd_active': "≡ƒÆ╗ ┬íModo CMD Activo!\nEnv├¡a cualquier comando para ejecutar en terminal.",
        'weather_usage': "≡ƒîñ∩╕Å Informaci├│n del Clima\n\nUso: /weather [nombre de ciudad]\nEjemplo: /weather Madrid",
        'search_usage': "≡ƒöì B├║squeda Web\n\nUso: /search [tu consulta]\nEjemplo: /search latest tech news",
        'ollama_mode': "≡ƒªÖ ┬íModo AI Local Ollama!\n\nAI Local Gratis - ┬íNo necesitas API key!\n\nEscribe cualquier mensaje y recibir├ís respuesta de IA!",
        'botprofile_help': "≡ƒñû **Gestor de Perfil del Bot**\n\n**Uso:**\n/botprofile name [nuevo_nombre]\n/botprofile description [texto]\n/botprofile about [texto]\n/botprofile photo\n/botprofile info",
    },
    'ar': {
        'welcome': "≡ƒæï ┘à╪▒╪¡╪¿╪º┘ï ╪¿┘â ┘ü┘è ╪¿┘ê╪¬ ╪ú┘ê╪¿┘å ┘â┘ä╪º┘ê╪»!\n\n╪ú┘å╪º ╪ú┘ä╪¿╪▒╪¬ ╪ú┘è┘å╪┤╪¬╪º┘è┘å╪î ┘à╪│╪º╪╣╪»┘â ╪º┘ä╪░┘â┘è.\n≡ƒîÉ ╪º┘ä╪¬╪¡┘â┘à ╪╣╪¿╪▒ ╪º┘ä┘ê┘è╪¿: {web_port}",
        'thinking': "≡ƒñû ╪¼╪º╪▒┘ì ╪º┘ä╪¬┘ü┘â┘è╪▒...",
        'error': "Γ¥î ╪«╪╖╪ú: {error}",
        'access_denied': "Γ¥î ╪¬┘à ╪▒┘ü╪╢ ╪º┘ä┘ê╪╡┘ê┘ä!\n┘à╪╣╪▒┘ü┘â: {user_id}\n╪ú╪╢┘ü ┘ç╪░╪º ╪Ñ┘ä┘ë ┘à┘ä┘ü .env ┘â┘Ç ALLOWED_USER_ID",
        'system_status': "≡ƒôè **╪¡╪º┘ä╪⌐ ╪º┘ä┘å╪╕╪º┘à**\n≡ƒûÑ CPU: {cpu}%\n≡ƒÆ╛ RAM: {ram}%\n≡ƒÆ╜ Disk: {disk}%",
        'help_title': "≡ƒôû **╪¿┘ê╪¬ ╪ú┘ê╪¿┘å ┘â┘ä╪º┘ê╪» - ╪º┘ä╪ú┘ê╪º┘à╪▒ ╪º┘ä┘â╪º┘à┘ä╪⌐:**",
        'ai_thinking': "≡ƒªÖ ╪ú┘ê┘ä╪º┘à╪º ({model}) ┘è┘ü┘â╪▒...",
        'ai_response': "≡ƒªÖ {response}",
        'cmd_active': "≡ƒÆ╗ ┘ê╪╢╪╣ CMD ┘å╪┤╪╖!\n╪ú╪▒╪│┘ä ╪ú┘è ╪ú┘à╪▒ ┘ä╪¬╪┤╪║┘è┘ä┘ç ┘ü┘è ╪º┘ä╪╖╪▒┘ü┘è╪⌐.",
        'weather_usage': "≡ƒîñ∩╕Å ┘à╪╣┘ä┘ê┘à╪º╪¬ ╪º┘ä╪╖┘é╪│\n\n╪º┘ä╪º╪│╪¬╪«╪»╪º┘à: /weather [╪º╪│┘à ╪º┘ä┘à╪»┘è┘å╪⌐]\n┘à╪½╪º┘ä: /weather ╪º┘ä┘é╪º┘ç╪▒╪⌐",
        'search_usage': "≡ƒöì ╪º┘ä╪¿╪¡╪½ ┘ü┘è ╪º┘ä┘ê┘è╪¿\n\n╪º┘ä╪º╪│╪¬╪«╪»╪º┘à: /search [╪º╪│╪¬┘ü╪│╪º╪▒┘â]\n┘à╪½╪º┘ä: /search latest tech news",
        'ollama_mode': "≡ƒªÖ ┘ê╪╢┘è AI ╪º┘ä┘à╪¡┘ä┘è ╪ú┘ê┘ä╪º┘à╪º!\n\nAI ┘à╪¡┘ä┘è ┘à╪¼╪º┘å┘è - ┘ä╪º ╪¬╪¡╪¬╪º╪¼ ┘à┘ü╪¬╪º╪¡ API!\n\n╪º┘â╪¬╪¿ ╪ú┘è ╪▒╪│╪º┘ä╪⌐ ┘ê╪º╪¡╪╡┘ä ╪╣┘ä┘ë ╪▒╪» AI!",
        'botprofile_help': "≡ƒñû **┘à╪»┘è╪▒ ┘à┘ä┘ü ╪º┘ä╪¿┘ê╪¬**\n\n**╪º┘ä╪º╪│╪¬╪«╪»╪º┘à:**\n/botprofile name [╪º╪│┘à_╪¼╪»┘è╪»]\n/botprofile description [┘å╪╡]\n/botprofile about [┘å╪╡]\n/botprofile photo\n/botprofile info",
    },
    'zh': {
        'welcome': "≡ƒæï µ¼óΦ┐ÄΣ╜┐τö¿ OpenClowd µ£║σÖ¿Σ║║!\n\nµêæµÿ»Θÿ┐σ░öΣ╝»τë╣┬╖τê▒σ¢áµû»σ¥ª∩╝îµé¿τÜä AI σè⌐µëïπÇé\n≡ƒîÉ τ╜æΘí╡µÄºσê╢: {web_port}",
        'thinking': "≡ƒñû µ¡úσ£¿µÇ¥ΦÇâ...",
        'error': "Γ¥î ΘöÖΦ»»: {error}",
        'access_denied': "Γ¥î Φ«┐Θù«Φó½µïÆτ╗¥!\nµé¿τÜäID: {user_id}\nΦ»╖σ░åσà╢µ╖╗σèáσê░.envµûçΣ╗╢Σ╕¡Σ╜£Σ╕║ ALLOWED_USER_ID",
        'system_status': "≡ƒôè **τ│╗τ╗ƒτè╢µÇü**\n≡ƒûÑ CPU: {cpu}%\n≡ƒÆ╛ RAM: {ram}%\n≡ƒÆ╜ Disk: {disk}%",
        'help_title': "≡ƒôû **OpenClowd µ£║σÖ¿Σ║║ - σ«îµò┤σæ╜Σ╗ñ:**",
        'ai_thinking': "≡ƒªÖ Ollama ({model}) µ¡úσ£¿µÇ¥ΦÇâ...",
        'ai_response': "≡ƒªÖ {response}",
        'cmd_active': "≡ƒÆ╗ CMD µ¿íσ╝Åσ╖▓µ┐Çµ┤╗!\nσÅæΘÇüΣ╗╗Σ╜òσæ╜Σ╗ñΣ╗Ñσ£¿τ╗êτ½»Σ╕¡Φ┐ÉΦíîπÇé",
        'weather_usage': "≡ƒîñ∩╕Å σñ⌐µ░öΣ┐íµü»\n\nτö¿µ│ò: /weather [σƒÄσ╕éσÉìτº░]\nτñ║Σ╛ï: /weather σîùΣ║¼",
        'search_usage': "≡ƒöì τ╜æΘí╡µÉ£τ┤ó\n\nτö¿µ│ò: /search [µé¿τÜäµƒÑΦ»ó]\nτñ║Σ╛ï: /search latest tech news",
        'ollama_mode': "≡ƒªÖ Ollama µ£¼σ£░ AI µ¿íσ╝Å!\n\nσàìΦ┤╣µ£¼σ£░ AI - µùáΘ£Ç API σ»åΘÆÑ!\n\nΦ╛ôσàÑΣ╗╗Σ╜òµ╢êµü»∩╝îµêæσ░åτö¿ AI σ¢₧σñì!",
        'botprofile_help': "≡ƒñû **µ£║σÖ¿Σ║║µíúµíêτ«íτÉåσÖ¿**\n\n**τö¿µ│ò:**\n/botprofile name [µû░σÉìτº░]\n/botprofile description [µûçµ£¼]\n/botprofile about [µûçµ£¼]\n/botprofile photo\n/botprofile info",
    }
}

def detect_language(text):
    """Detect language from text"""
    # Bengali Unicode range
    if any('\u0980' <= char <= '\u09FF' for char in text):
        return 'bn'
    # Hindi Unicode range
    elif any('\u0900' <= char <= '\u097F' for char in text):
        return 'hi'
    # Arabic Unicode range
    elif any('\u0600' <= char <= '\u06FF' for char in text):
        return 'ar'
    # Chinese Unicode range
    elif any('\u4e00' <= char <= '\u9fff' for char in text):
        return 'zh'
    # Spanish/French common words detection could be added here
    else:
        return 'en'  # Default to English

def get_text(key, lang='en', **kwargs):
    """Get translated text"""
    if lang not in LANGUAGES:
        lang = 'en'
    
    text = LANGUAGES[lang].get(key, LANGUAGES['en'].get(key, key))
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    
    return text

def get_language_name(lang_code):
    """Get language name from code"""
    names = {
        'en': '≡ƒç¼≡ƒçº English',
        'bn': '≡ƒçº≡ƒç⌐ αª¼αª╛αªéαª▓αª╛ (Bengali)',
        'hi': '≡ƒç«≡ƒç│ αñ╣αñ┐αñ¿αÑìαñªαÑÇ (Hindi)',
        'es': '≡ƒç¬≡ƒç╕ Espa├▒ol (Spanish)',
        'ar': '≡ƒç╕≡ƒçª ╪º┘ä╪╣╪▒╪¿┘è╪⌐ (Arabic)',
        'zh': '≡ƒç¿≡ƒç│ Σ╕¡µûç (Chinese)'
    }
    return names.get(lang_code, 'Unknown')

