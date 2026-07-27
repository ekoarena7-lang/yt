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

# --- AUTOMATIC LINK CAPTION & TEXT SCRAPER ---
def extract_youtube_id(url):
    pattern = r"(?:v=|\/\|vi=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def fetch_link_caption(url):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "tr-TR,tr;q=0.9,az;q=0.8,en-US;q=0.7,en;q=0.6"
    }
    extracted_text = ""

    if "youtube.com" in url or "youtu.be" in url:
        try:
            res = requests.get(f"https://www.youtube.com/oembed?url={url}&format=json", headers=headers, timeout=10)
            if res.status_code == 200:
                extracted_text = res.json().get("title", "")
        except Exception:
            pass

        video_id = extract_youtube_id(url)
        if video_id:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                t_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['az', 'tr', 'en'])
                t_text = " ".join([item['text'] for item in t_list])
                extracted_text = f"{extracted_text} {t_text}".strip()
            except Exception:
                pass

    if not extracted_text:
        try:
            res = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
            if res.status_code == 200:
                html = res.text
                meta_matches = re.findall(r'<meta\s+(?:property|name)=["\'](?:og:description|description|og:title|twitter:description)["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if meta_matches:
                    clean_matches = [m.strip() for m in meta_matches if len(m.strip()) > 8 and "Instagram" not in m and "TikTok" not in m]
                    if clean_matches:
                        extracted_text = " ".join(clean_matches)
        except Exception as e:
            print(f"Scraping error: {e}")

    if not extracted_text:
        try:
            oembed_res = requests.get(f"https://noembed.com/embed?url={url}", headers=headers, timeout=10)
            if oembed_res.status_code == 200:
                extracted_text = oembed_res.json().get("title", "")
        except Exception:
            pass

    return extracted_text if extracted_text else url

def build_dynamic_repurpose(input_text):
    lines = [l.strip() for l in input_text.split("\n") if len(l.strip()) > 5]
    if not lines:
        lines = [input_text]

    first_line = lines[0]
    middle_lines = " ".join(lines[1:4]) if len(lines) > 1 else first_line
    full_text = " ".join(lines)

    hook = first_line[:80]
    voice_script = middle_lines[:160] if len(middle_lines) > 20 else full_text[:160]
    x_post = full_text[:270]
    linkedin_article = full_text[:600]

    return f"""🎬 <b>1. Shorts / Reels Ssenarisi:</b>
• <b>Hook:</b> {hook}
• <b>Səs Mətni:</b> {voice_script}...
• <b>Vizual:</b> 9:16 vertikal dinamik kadrlar.

🐦 <b>2. X (Twitter) Postu:</b>
{x_post}... #YITX #Gündəm

💼 <b>3. LinkedIn Məqaləsi:</b>
{linkedin_article}

#YITX #SocialMedia #Repurpose #AI"""

def generate_ai_repurpose(video_caption):
    # Try Gemini LLM if valid key exists
    if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIzaSy"):
        prompt = f"Sən YİTX AI Multi-Platform Repurposer-isən. Bu məzmunu 3 hissəyə böl (Shorts Ssenarisi, X postu, LinkedIn Məqaləsi):\n\n{video_caption}"
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

    # Dynamic context parser guarantees 100% exact topic match
    return build_dynamic_repurpose(video_caption)

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
            repurposed_text = generate_ai_repurpose(scraped_caption)
        else:
            repurposed_text = generate_ai_repurpose(user_text)

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
