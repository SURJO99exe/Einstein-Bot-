import re
import requests
import os
import time
import asyncio
import httpx

# Mini AI Knowledge Base
MINI_AI_KNOWLEDGE = {
    "who are you": "I am Einstein System, a mini-AI developed to assist you with tasks, moderation, and chat!",
    "what can you do": "I can moderate servers, track XP, manage economy, notify social media updates, and talk to you!",
    "help": "You can type `!bothelp` to see a full list of my commands!",
    "creator": "I was created to be a powerful assistant for the SURJO LIVE server.",
    "owner": "My owner is the administrator of this server. You can find them in the member list!",
    "weather": "I can check the weather if you use my Telegram version or wait for my next Discord update!",
    "time": "You can use `!time` to see the current time and date.",
    "joke": "Try `!joke` for a scientific laugh!",
    "fact": "Type `!fact` to learn something new about science!",
    "ping": "Use `!ping` to check my response speed.",
    "version": "I am currently running on Einstein-Bot Version 3.5.0.",
    "status": "Check `!status` to see my system health and resource usage."
}

def analyze_and_reply_mini_ai(question):
    """Mini AI logic to analyze and reply to user questions locally"""
    q = question.lower()
    
    # 1. Keywords mapping
    for key, response in MINI_AI_KNOWLEDGE.items():
        if key in q:
            return response

    # 2. Simple Math Analysis
    math_pattern = re.search(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", q)
    if math_pattern:
        try:
            num1 = int(math_pattern.group(1))
            op = math_pattern.group(2)
            num2 = int(math_pattern.group(3))
            if op == '+': res = num1 + num2
            elif op == '-': res = num1 - num2
            elif op == '*': res = num1 * num2
            elif op == '/': res = num1 / num2 if num2 != 0 else "undefined"
            return f"I analyzed your math question: {num1} {op} {num2} = {res}"
        except:
            pass

    # 3. Fallback for unknown questions
    if "?" in q:
        return "That's an interesting question! I don't have a specific local answer for that yet, but I'm learning every day. Try asking something about my features!"
        
    return None

async def get_ai_response_discord(user_id, message_content, discord_conversations, personality_prompt, ollama_model, max_tokens=80):
    """Get AI response for Discord with conversation memory"""
    # Try Mini AI first
    mini_response = analyze_and_reply_mini_ai(message_content)
    if mini_response:
        return mini_response

    try:
        user_id_str = str(user_id)
        if user_id_str not in discord_conversations:
            discord_conversations[user_id_str] = []
        
        discord_conversations[user_id_str].append({"role": "user", "content": message_content})
        
        if len(discord_conversations[user_id_str]) > 5:
            discord_conversations[user_id_str] = discord_conversations[user_id_str][-5:]

        # 1. Try OpenAI if key exists
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_api_key_here":
            try:
                headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "system", "content": personality_prompt}] + discord_conversations[user_id_str],
                    "max_tokens": max_tokens
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
                    if resp.status_code == 200:
                        reply = resp.json()['choices'][0]['message']['content'].strip()
                        discord_conversations[user_id_str].append({"role": "assistant", "content": reply})
                        return reply
            except Exception as e:
                print(f"DEBUG: OpenAI error: {e}")

        # 2. Fallback to Pollinations AI (Free)
        try:
            pollinations_url = f"https://text.pollinations.ai/{personality_prompt} {message_content}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(pollinations_url, timeout=10)
                if resp.status_code == 200:
                    reply = resp.text.strip()
                    discord_conversations[user_id_str].append({"role": "assistant", "content": reply})
                    return reply
        except Exception as p_err:
            print(f"DEBUG: Pollinations fallback error: {p_err}")

        # 3. Fallback to Ollama
        try:
            context_text = "\n".join([f"{'User' if m['role'] == 'user' else 'You'}: {m['content']}" for m in discord_conversations[user_id_str][:-1]])
            current_message = discord_conversations[user_id_str][-1]["content"]
            
            ollama_prompt = f"{personality_prompt}\n\nPrevious conversation:\n{context_text}\n\nUser just said: {current_message}\n\nReply naturally:"
            
            resp = requests.post(
                f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": ollama_prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                },
                timeout=10
            )
            if resp.status_code == 200:
                reply = resp.json().get('response', '').strip()
                discord_conversations[user_id_str].append({"role": "assistant", "content": reply})
                return reply
        except Exception as o_err:
            print(f"DEBUG: Ollama fallback error: {o_err}")
        
        return "I'm here! How can I help you today? 😊" 

    except Exception as e:
        print(f"DEBUG: AI response error: {e}")
        return None
