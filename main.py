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

# --- AI GEMINI TEXT GENERATOR ---
def generate_ai_text(prompt, system_instruction="Sen YİTX Otomasyonu AI kontent asistanısan. Sosyal medya için yüksek etkileşimli içerikler hazırlıyorsun."):
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": f"{system_instruction}\n\nİstək/Konu: {prompt}\n\nLütfən cavabı JSON formatında qaytar:\n{{\"hook\": \"...\", \"caption\": \"...\", \"hashtags\": \"...\"}} "}]
            }]
        }
        try:
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
            if res.status_code == 200:
                text_content = res.json()['candidates'][0]['content']['parts'][0]['text']
                if "```json" in text_content:
                    text_content = text_content.split("```json")[1].split("```")[0].strip()
                elif "```" in text_content:
                    text_content = text_content.split("```")[1].split("```")[0].strip()
                return json.loads(text_content)
        except Exception as e:
            print(f"Gemini error with {model}: {e}")

    return {
        "hook": f"💡 YİTX AI: {prompt[:40]}",
        "caption": f"{prompt}\n\nYİTX Otomasyonu tərəfindən emal olundu.",
        "hashtags": "#YITX #Automation #AI #Content"
    }

# --- REPURPOSER ---
def repurpose_content(source_url):
    prompt = f"""
    Aşağıdakı video məzmununu (YouTube / Instagram Reels / TikTok) sosial media üçün yenidən işlə (Content Repurposing - YİTX Otomasyonu):

    MƏZMUN / LİNK:
    {source_url}

    XAHİŞ OLUNUR AŞAĞIDAKILARI YARAT VƏ STRUKTUR İLƏ QAYTAR:
    1. 3 ədəd Shorts/Reels/TikTok Video Ssenarisi (Hook, Səs mətni, Visual prompt)
    2. 5 ədəd X (Twitter) Postu
    3. 2 ədəd LinkedIn Məqaləsi
    """
    return generate_ai_text(prompt, system_instruction="Sen YİTX Multi-Platform Repurposer-isən. YouTube, Instagram Reels və TikTok videolarını viral postlara çevirirsən.")

# --- TELEGRAM BOT LOGIC ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

def is_url(text):
    return bool(re.search(r"https?://[^\s]+", text))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_html = (
        "🤖 <b>YİTX Otomasyonu — AI Kontent Botu Canlıdır!</b>\n\n"
        "İstənilən <b>YouTube, Instagram Reels və ya TikTok video linkini</b> sadəcə bura göndərin!\n\n"
        "📌 <b>İstifadə:</b>\n"
        "• Link göndərin ➔ Avtomatik Repurpose edir.\n"
        "• Mövzu yazın ➔ AI mətn və post yazır.\n"
    )
    await update.message.reply_text(welcome_html, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if text.startswith("/"):
        return

    try:
        if is_url(text):
            await update.message.reply_text("🔄 <b>YİTX:</b> Video təhlil olunur və məzmunlar yenidən işlənilir...", parse_mode='HTML')
            res = repurpose_content(text)
            hook = res.get("hook", "YİTX Repurpose")
            caption = res.get("caption", "")
            tags = res.get("hashtags", "")
            await update.message.reply_text(f"🎬 <b>{hook}</b>\n\n{caption}\n\n<i>{tags}</i>", parse_mode='HTML')
        else:
            await update.message.reply_text("⏳ <b>YİTX AI:</b> Mətn hazırlanır...", parse_mode='HTML')
            res = generate_ai_text(text)
            hook = res.get("hook", "YİTX Post")
            caption = res.get("caption", "")
            tags = res.get("hashtags", "")
            await update.message.reply_text(f"📝 <b>{hook}</b>\n\n{caption}\n\n<i>{tags}</i>", parse_mode='HTML')
    except Exception as e:
        traceback.print_exc()
        await update.message.reply_text(f"⚠️ Xəta: {str(e)}", parse_mode='HTML')

def main():
    init_db()
    print("🚀 YİTX Telegram Bot Starting (Polling mode)...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
