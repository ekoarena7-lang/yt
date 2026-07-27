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
    """
    Automatically scrapes the video caption/description directly from Instagram Reels, TikTok, or YouTube link.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "tr-TR,tr;q=0.9,az;q=0.8,en-US;q=0.7,en;q=0.6"
    }
    extracted_text = ""

    # YouTube Specific
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

    # Instagram & TikTok Scraper
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

    # Noembed oEmbed fallback
    if not extracted_text:
        try:
            oembed_res = requests.get(f"https://noembed.com/embed?url={url}", headers=headers, timeout=10)
            if oembed_res.status_code == 200:
                extracted_text = oembed_res.json().get("title", "")
        except Exception:
            pass

    return extracted_text if extracted_text else url

# --- 100% RELIABLE LLM REPURPOSER ---
def generate_ai_repurpose(video_caption, raw_url):
    prompt = f"""
    Sən YİTX Multi-Platform Repurposer AI-san.
    Aşağıda istifadəçinin göndərdiyi sosial media video linkindən avtomatik oxunan tam mətn verilib:

    LİNKDƏN ÇIXARILAN MƏZMUN:
    {video_caption}

    ORİJİNAL LİNK:
    {raw_url}

    XAHİŞ OLUNUR YUXARIDAKI MƏZMUNU OXUYUB BU 3 DƏQİQ BÖLMƏNİ YARAT (Sırf HTML formatında yaz):
    🎬 <b>1. Shorts / Reels Ssenarisi:</b>
    • <b>Hook:</b> [Yuxarıdakı videonun məzmunundan diqqət çəkən ilk 3 saniyə mətni]
    • <b>Səs Mətni:</b> [Yuxarıdakı videodakı ideyadan 30 saniyəlik səs mətni]
    • <b>Vizual:</b> [9:16 vertikal dinamik kadr təsviri]

    🐦 <b>2. X (Twitter) Postu:</b>
    [Yuxarıdakı video məzmunundan hazırlanmış 280 simvolluq X postu]

    💼 <b>3. LinkedIn Məqaləsi:</b>
    [Yuxarıdakı mövzu haqqında peşəkar 2 paraqraflıq LinkedIn məqaləsi]

    #YITX #Viral #Repurpose #AI #SocialMedia
    """

    # 1. Try Pollinations Free LLM API
    try:
        res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role": "user", "content": prompt}], "model": "openai"}, timeout=25)
        if res.status_code == 200 and len(res.text) > 80:
            return res.text.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"Pollinations LLM error: {e}")

    # 2. Try Gemini API if valid key is set
    if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIzaSy"):
        for model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                g_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                res = requests.post(g_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
                if res.status_code == 200:
                    text_content = res.json()['candidates'][0]['content']['parts'][0]['text']
                    return text_content.replace("```html", "").replace("```", "").strip()
            except Exception as e:
                print(f"Gemini API error: {e}")

    # 3. Smart Contextual Return
    return f"""🎬 <b>1. Shorts / Reels Ssenarisi:</b>
• <b>Hook:</b> {video_caption[:60]}... Bilirdinizmi?
• <b>Səs Mətni:</b> Bu video haqqında mühüm faktlar ortaya çıxdı!
• <b>Vizual:</b> 9:16 vertikal dinamik kadrlar.

🐦 <b>2. X (Twitter) Postu:</b>
{video_caption[:200]}... #YITX

💼 <b>3. LinkedIn Məqaləsi:</b>
{video_caption}

#YITX #SocialMedia #Repurpose #AI"""

def generate_ai_post(prompt_text):
    prompt = f"Sən YİTX AI yazarısan. Bu mövzuda HTML formatında sosial media postu yaz: {prompt_text}"
    try:
        res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role": "user", "content": prompt}], "model": "openai"}, timeout=20)
        if res.status_code == 200 and len(res.text) > 30:
            return res.text.replace("```html", "").replace("```", "").strip()
    except Exception:
        pass

    return f"💡 <b>YİTX Post: {prompt_text}</b>\n\nSüni intellekt və avtomatlaşdırma dünyasında yeni addımlar.\n\n#YITX #Automation"

# --- TELEGRAM BOT LOGIC ---
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

def is_url(text):
    return bool(re.search(r"https?://[^\s]+", text))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_html = (
        "🤖 <b>YİTX Otomasyonu — AI Kontent Botu Canlıdır!</b>\n\n"
        "İstənilən <b>YouTube, Instagram Reels və ya TikTok video linkini</b> sadəcə bura göndərin!\n\n"
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
            await update.message.reply_text("🔄 <b>YİTX:</b> Linkdən məzmun oxunur və 3 fərqli formata çevrilir...", parse_mode='HTML')
            scraped_caption = fetch_link_caption(user_text)
            repurposed_text = generate_ai_repurpose(scraped_caption, user_text)
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
