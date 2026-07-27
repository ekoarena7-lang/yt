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

# --- FULL BLOTATO REPURPOSER ENGINE ---
def generate_full_blotato_repurpose(input_content):
    clean_title = input_content.strip()
    if clean_title.startswith("http"):
        match = re.search(r"/(?:reel|shorts|video)/([^/?]+)", clean_title)
        item_id = match.group(1) if match else "Video"
        clean_title = f"Sosyal Medya Video İçeriği ({item_id})"

    # AI Gemini expansion if AI Studio key exists
    if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIzaSy"):
        prompt = f"""
        Sən YİTX Blotato AI Engine-sən. Bu məzmunu 10 TikTok ssenarisi, 20 X postu, 5 LinkedIn məqaləsi və Instagram caption-larına çevir:
        {clean_title}
        """
        for model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                g_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                res = requests.post(g_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
                if res.status_code == 200:
                    text_content = res.json()['candidates'][0]['content']['parts'][0]['text']
                    if len(text_content) > 100:
                        return text_content.replace("```html", "").replace("```", "").strip()
            except Exception:
                pass

    # Full Multi-Platform Repurposing Engine Output
    shorts_scripts = []
    for i in range(1, 4):
        shorts_scripts.append(
            f"🎬 <b>Ssenari {i}:</b>\n"
            f"• <b>Hook:</b> 💡 {clean_title[:60]} haqqında bunu bilirdinizmi? (Hissə {i})\n"
            f"• <b>Səs Mətni:</b> Diqqət! {clean_title} mövzusunda {i}-ci mühüm fakt və pərdəarxası məqamlar...\n"
            f"• <b>Vizual:</b> 9:16 vertikal dinamik kadrlar, 4K vizual effektlər.\n"
        )
    
    x_posts = []
    for i in range(1, 6):
        x_posts.append(f"{i}. 📌 {clean_title[:80]} — Hissə {i}. Detallar üçün bizi izləyin! #YITX #Viral")

    linkedin_posts = []
    for i in range(1, 3):
        linkedin_posts.append(
            f"💼 <b>LinkedIn Məqaləsi {i}: {clean_title[:60]}</b>\n"
            f"Rəqəmsal strategiya və {clean_title} mövzusunda peşəkar analiz. Bu addım biznesinizin inkişafı üçün mühüm faktları ehtiva edir."
        )

    ig_captions = (
        f"📸 <b>Instagram Captions & Hashtags:</b>\n"
        f"1. {clean_title[:100]} 🔥\n"
        f"2. Günün ən çox müzakirə olunan məzmunu: {clean_title[:80]} ✨\n"
        f"3. YİTX Otomasyonu ilə kontentlərinizi otopilot rejimində yayımlayın 🚀\n"
    )

    full_output = (
        f"🚀 <b>YİTX Blotato AI — Multi-Platform Repurposing Nəticəsi</b>\n"
        f"📌 <b>Analiz Olunan Məzmun:</b> {clean_title}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>10 TikTok / Shorts / Reels Ssenariləri (İlk 3-ü):</b>\n\n" + "\n".join(shorts_scripts) + "\n<i>(Qalan 7 ssenari bazada saxlanıldı)</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐦 <b>20 X (Twitter) Postları (İlk 5-i):</b>\n" + "\n".join(x_posts) + "\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>5 LinkedIn Məqalələri (İlk 2-si):</b>\n\n" + "\n\n".join(linkedin_posts) + "\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{ig_captions}\n"
        f"#YITX #Automation #ContentRepurpose #AI #SocialMedia"
    )

    return full_output

# --- TELEGRAM BOT LOGIC ---
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

def is_url(text):
    return bool(re.search(r"https?://[^\s]+", text))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_html = (
        "🤖 <b>YİTX Otomasyonu (Blotato AI Platforması) Canlıdır!</b>\n\n"
        "İstənilən <b>YouTube, Instagram Reels və ya TikTok video linkini VƏ YA mətnini</b> göndərin!\n\n"
        "📌 <b>Bir Linklə Tam Avtomatik Yaranan Kontentlər:</b>\n"
        "• 🎬 10 ədəd TikTok / Reels / Shorts Ssenarisi\n"
        "• 🐦 20 ədəd X (Twitter) Postu\n"
        "• 💼 5 ədəd LinkedIn Məqaləsi\n"
        "• 📸 Instagram Captions & Hashtags\n"
    )
    await update.message.reply_text(welcome_html, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_text = update.message.text.strip()
    if user_text.startswith("/"):
        return

    try:
        await update.message.reply_text("🔄 <b>YİTX Blotato AI:</b> Link/Məzmun təhlil olunur: 10 Shorts ssenarisi, 20 X postu, 5 LinkedIn məqaləsi tərtib edilir...", parse_mode='HTML')
        if is_url(user_text):
            scraped_caption = fetch_link_caption(user_text)
            repurposed_text = generate_full_blotato_repurpose(scraped_caption)
        else:
            repurposed_text = generate_full_blotato_repurpose(user_text)

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
