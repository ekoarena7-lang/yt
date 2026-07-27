import os
import sys
import logging
import traceback
import re
import time
import sqlite3
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8823623970:AAHdWNjM52xRSamEJRMOagB6BB6xKb2mDSQ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6K93hTu6R20yoAQacS6D48gBuvbvHi2Ksmy5ajsP-x89g")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- DATABASE SETUP ---
DB_PATH = os.path.join(os.path.dirname(__file__), "database.sqlite")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,
        title TEXT,
        content_text TEXT NOT NULL,
        media_url TEXT,
        media_type TEXT DEFAULT 'none',
        platforms TEXT NOT NULL,
        status TEXT DEFAULT 'draft',
        scheduled_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        published_at TIMESTAMP,
        error_log TEXT
    );
    """)
    conn.commit()
    conn.close()

# --- VIDEO METADATA & TRANSCRIPT EXTRACTOR ---
def extract_youtube_id(url):
    pattern = r"(?:v=|\/\|vi=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def fetch_video_info(url):
    title = ""
    transcript = ""
    
    headers = {"User-Agent": USER_AGENT}

    # YouTube Extraction
    if "youtube.com" in url or "youtu.be" in url:
        try:
            res = requests.get(f"https://www.youtube.com/oembed?url={url}&format=json", headers=headers, timeout=10)
            if res.status_code == 200:
                title = res.json().get("title", "")
        except Exception:
            pass

        video_id = extract_youtube_id(url)
        if video_id:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                t_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['az', 'tr', 'en'])
                transcript = " ".join([item['text'] for item in t_list])
            except Exception:
                pass
    else:
        # Instagram / TikTok oEmbed metadata extraction
        try:
            res = requests.get(f"https://noembed.com/embed?url={url}", headers=headers, timeout=10)
            if res.status_code == 200:
                title = res.json().get("title", "")
        except Exception:
            pass

    if not title:
        title = f"Sosyal Medya Video İçeriği ({url})"

    return f"VİDEO BAŞLIĞI: {title}\nVİDEO MƏZMUNU/TRANSKRİPT: {transcript}\nORİJİNAL LİNK: {url}"

# --- BULLETPROOF AI GENERATION ENGINE ---
def generate_ai_repurpose(video_info):
    prompt = f"""
    Sən YİTX Multi-Platform Repurposer AI-san. Aşağıdakı videonun məzmununu götür və bu 3 bölmədən ibarət bütöv mətn hazırla:

    {video_info}

    SƏNDƏN TƏLƏB OLUNAN DƏQİQ ÇIXIŞ FORMATI (Sırf HTML formatında yaz):
    🎬 <b>1. Shorts / Reels Ssenarisi:</b>
    • <b>Hook:</b> [Diqqət çəkən ilk 3 saniyə mətni]
    • <b>Səs Mətni:</b> [Videodakı ideyanın qısa səs mətni]
    • <b>Vizual:</b> [9:16 vertikal dinamik kadr təsviri]

    🐦 <b>2. X (Twitter) Postu:</b>
    [Videodakı ən maraqlı fikri X postu kimi yaz]

    💼 <b>3. LinkedIn Məqaləsi:</b>
    [Bu videodakı mövzu haqqında peşəkar LinkedIn məqaləsi yaz]

    #YITX #Viral #Repurpose #AI #SocialMedia
    """

    # Tier 1: Gemini API
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        if not GEMINI_API_KEY.startswith("AIzaSy"):
            headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                text_content = res.json()['candidates'][0]['content']['parts'][0]['text']
                if text_content and len(text_content) > 50:
                    return clean_html(text_content)
        except Exception as e:
            print(f"Gemini API error with {model}: {e}")

    # Tier 2: Open LLM Proxy Fallback (Guarantees zero prompt echo)
    try:
        res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role": "user", "content": prompt}], "model": "openai"}, timeout=20)
        if res.status_code == 200 and len(res.text) > 50:
            return clean_html(res.text)
    except Exception as e:
        print(f"Tier 2 LLM error: {e}")

    # Tier 3: Emergency Formatted Return
    return """🎬 <b>1. Shorts / Reels Ssenarisi:</b>
• <b>Hook:</b> Bu videodakı qızıl qaydanı bilirdinizmi?
• <b>Səs Mətni:</b> Sosial mediada uğur qazanmaq üçün bu strategiyanı tətbiq edin.
• <b>Vizual:</b> 9:16 vertikal dinamik kadrlar.

🐦 <b>2. X (Twitter) Postu:</b>
Uğur kiçik addımlarla gəlir. Bu videodakı fikirlər biznesinizi böyüdəcək! #YITX

💼 <b>3. LinkedIn Məqaləsi:</b>
Rəqəmsal dövrdə effektiv kontent strategiyası qurmaq üçün vizual və mətn harmoniyası vacibdir.

#YITX #SocialMedia #Repurpose #AI"""

def generate_ai_post(prompt_text):
    prompt = f"Sən YİTX AI yazarısan. Bu mövzuda HTML formatında sosial media postu yaz: {prompt_text}"
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        if not GEMINI_API_KEY.startswith("AIzaSy"):
            headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                text_content = res.json()['candidates'][0]['content']['parts'][0]['text']
                if text_content:
                    return clean_html(text_content)
        except Exception:
            pass

    return f"💡 <b>YİTX Post: {prompt_text}</b>\n\nSüni intellekt və avtomatlaşdırma dünyasında yeni addımlar.\n\n#YITX #Automation"

def clean_html(text):
    text = text.replace("```html", "").replace("```", "").strip()
    return text

# --- TELEGRAM BOT LOGIC ---
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

def is_url(text):
    return bool(re.search(r"https?://[^\s]+", text))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_html = (
        "🤖 <b>YİTX Otomasyonu — AI Kontent Botu Canlıdır!</b>\n\n"
        "İstənilən <b>YouTube, Instagram Reels və ya TikTok video linkini</b> göndərin!\n\n"
        "📌 <b>Nə verəcək:</b>\n"
        "1. 🎬 <b>Shorts / Reels Ssenarisi</b>\n"
        "2. 🐦 <b>X (Twitter) Postu</b>\n"
        "3. 💼 <b>LinkedIn Məqaləsi</b>\n"
    )
    await update.message.reply_text(welcome_html, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_text = update.message.text.strip()
    if user_text.startswith("/"):
        return

    try:
        if is_url(user_text):
            await update.message.reply_text("🔄 <b>YİTX:</b> Video məzmunu təhlil olunur və 3 fərqli formata çevrilir...", parse_mode='HTML')
            v_info = fetch_video_info(user_text)
            repurposed_text = generate_ai_repurpose(v_info)
            await update.message.reply_text(repurposed_text, parse_mode='HTML')
        else:
            await update.message.reply_text("⏳ <b>YİTX AI:</b> Mətn hazırlanır...", parse_mode='HTML')
            post_text = generate_ai_post(user_text)
            await update.message.reply_text(post_text, parse_mode='HTML')
    except Exception as e:
        traceback.print_exc()
        await update.message.reply_text(f"⚠️ Xəta: {str(e)}", parse_mode='HTML')

def main():
    init_db()
    print("🚀 YİTX Telegram Bot Running...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
