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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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

# --- LINK SCRAPER & TITLE EXTRACTOR ---
def extract_youtube_id(url):
    pattern = r"(?:v=|\/\|vi=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def fetch_link_caption(url):
    headers = {"User-Agent": USER_AGENT}
    
    # 1. YouTube Shorts & Video oEmbed
    if "youtube.com" in url or "youtu.be" in url:
        clean_url = url.split("?")[0]
        try:
            res = requests.get(f"https://www.youtube.com/oembed?url={clean_url}&format=json", headers=headers, timeout=10)
            if res.status_code == 200:
                title = res.json().get("title", "")
                if title:
                    return title
        except Exception:
            pass

        video_id = extract_youtube_id(url)
        if video_id:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                t_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['az', 'tr', 'en'])
                t_text = " ".join([item['text'] for item in t_list])
                if t_text:
                    return t_text[:300]
            except Exception:
                pass

    # 2. Instagram & TikTok oEmbed fallback
    try:
        clean_url = url.split("?")[0]
        res = requests.get(f"https://noembed.com/embed?url={clean_url}", headers=headers, timeout=10)
        if res.status_code == 200:
            title = res.json().get("title", "")
            if title and not title.startswith("http") and "Instagram" not in title:
                return title
    except Exception:
        pass

    return url

# --- SMART DYNAMIC REPURPOSER ENGINE ---
def smart_repurpose_engine(input_content):
    # Check if AI Studio key exists
    if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIzaSy"):
        prompt = f"Sən YİTX AI Multi-Platform Repurposer-isən. Bu məzmunu 3 hissəyə böl (Shorts Ssenarisi, X postu, LinkedIn Məqaləsi):\n\n{input_content}"
        for model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                g_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                res = requests.post(g_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
                if res.status_code == 200:
                    text_content = res.json()['candidates'][0]['content']['parts'][0]['text']
                    if len(text_content) > 50:
                        return text_content.replace("```html", "").replace("```", "").strip()
            except Exception:
                pass

    # Clean URL if passed as title
    if input_content.startswith("http"):
        match = re.search(r"/(?:reel|shorts|video)/([^/?]+)", input_content)
        item_id = match.group(1) if match else "Məzmun"
        clean_title = f"Sosyal Medya Trendi ({item_id})"
    else:
        clean_title = input_content.strip()

    lines = [l.strip() for l in clean_title.split("\n") if len(l.strip()) > 3]
    first_sentence = lines[0] if lines else clean_title
    full_text = " ".join(lines) if len(lines) > 1 else clean_title

    hook_text = first_sentence[:80]
    script_voice = (
        f"Diqqət! {first_sentence[:100]} haqqında ən son məlumatlar və pərdəarxası məqamlar ortaya çıxdı. "
        f"Bu məzmunda qeyd olunan faktlar sosial mediada böyük maraq doğurub. "
        f"Detalları bilmək üçün videonu axıra qədər izləyin!"
    )
    
    x_post = (
        f"🔥 {first_sentence[:150]}\n\n"
        f"Günün ən çox müzakirə olunan rəqəmsal kontenti! "
        f"Detallar haqqında nə düşünürsünüz? #YITX #Viral #Gündəm"
    )
    
    linkedin_article = (
        f"📊 <b>Biznes və Kontent Analizi: {first_sentence[:100]}</b>\n\n"
        f"Bugünkü rəqəmsal trendlərdə {full_text[:300]} mövzusu xüsusi diqqət cəlb edir. "
        f"Brendlər və kontent yaradıcıları üçün bu cür dinamik məzmunlar auditoriya ilə qarşılıqlı təsiri 3 dəfə artırır."
    )

    return f"""🎬 <b>1. Shorts / Reels Ssenarisi:</b>
• <b>Hook:</b> 💡 {hook_text}
• <b>Səs Mətni:</b> {script_voice}
• <b>Vizual:</b> 9:16 vertikal dinamik kadrlar və 4K vizual effektlər.

🐦 <b>2. X (Twitter) Postu:</b>
{x_post}

💼 <b>3. LinkedIn Məqaləsi:</b>
{linkedin_article}

#YITX #SocialMedia #Repurpose #AI"""

# --- TELEGRAM BOT LOGIC ---
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

def is_url(text):
    return bool(re.search(r"https?://[^\s]+", text))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_html = (
        "🤖 <b>YİTX Otomasyonu — AI Kontent Botu Canlıdır!</b>\n\n"
        "İstənilən <b>YouTube, Instagram Reels və ya TikTok video linkini VƏ YA mətnini</b> göndərin!\n\n"
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
        await update.message.reply_text("🔄 <b>YİTX:</b> Məzmun təhlil olunur və 3 fərqli formata çevrilir...", parse_mode='HTML')
        if is_url(user_text):
            scraped_caption = fetch_link_caption(user_text)
            repurposed_text = smart_repurpose_engine(scraped_caption)
        else:
            repurposed_text = smart_repurpose_engine(user_text)

        await update.message.reply_text(repurposed_text, parse_mode='HTML')
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
