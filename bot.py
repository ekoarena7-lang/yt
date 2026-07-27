import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from db.database import init_db, add_post, update_post_status, get_pending_scheduled_posts
from core.text_generator import generate_ai_text
from core.media_engine import generate_image, generate_video
from core.repurposer import repurpose_content
from core.social_publisher import publish_to_platforms

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *YİTX Otomasyonu — AI Kontent & Sosial Media Botuna Xoş Gəldiniz!*\n\n"
        "Bütün sosial media məzmun yaratma və paylaşım prosesini Buradan idarə edə bilərsiniz:\n\n"
        "📌 *Əsas Komandalar:*\n"
        "• `/post <konu>` — AI ilə mətn, şəkil və video hazırlayır.\n"
        "• `/repurpose <YouTube_URL>` — 1 YouTube videosunu TikTok/Reels, X və LinkedIn üçün uyğunlaşdırır.\n"
        "• `/queue` — Növbədə olan və planlaşdırılmış postları göstərir.\n"
        "• `/help` — Kömək və təlimatlar.\n"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💡 *YİTX Otomasyonu İstifadə Qaydası:*\n\n"
        "1. Sadəcə bir mövzu yazın və ya `/post` komandası göndərin.\n"
        "2. AI avtomatik olaraq Hook, Caption və AI Görsel/Video hazırlayacaq.\n"
        "3. Ekranda çıxan düymələr ilə anında paylaşa və ya planlaşdıra bilərsiniz."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args) if context.args else update.message.text
    if not prompt or prompt.startswith("/"):
        await update.message.reply_text("Lütfən bir mövzu və ya ideya qeyd edin. Məsələn: `/post 2026-cı ildə AI trendləri`", parse_mode='Markdown')
        return

    await update.message.reply_text("⏳ YİTX AI Mətn və Media hazırlayır, xahiş olunur gözləyin...")

    res_text = generate_ai_text(prompt)
    caption = f"{res_text.get('hook', '')}\n\n{res_text.get('caption', '')}\n\n{res_text.get('hashtags', '')}"
    media_url = generate_image(prompt)

    post_id = add_post(
        source_type='prompt',
        title=res_text.get('hook', 'YİTX AI Post'),
        content_text=caption,
        platforms='ig,tiktok,youtube,x,linkedin',
        media_url=media_url,
        media_type='image',
        status='draft'
    )

    keyboard = [
        [
            InlineKeyboardButton("🚀 Anında Paylaş", callback_data=f"publish_{post_id}"),
            InlineKeyboardButton("📅 Planlaşdır (1 Saat)", callback_data=f"schedule_{post_id}")
        ],
        [
            InlineKeyboardButton("❌ Ləğv Et", callback_data=f"cancel_{post_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=media_url,
        caption=f"📝 *YİTX AI Hazırladığı Post (ID #{post_id}):*\n\n{caption}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def repurpose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = " ".join(context.args) if context.args else ""
    if not url:
        await update.message.reply_text("Lütfən bir YouTube linki qeyd edin. Məsələn: `/repurpose https://youtu.be/...`", parse_mode='Markdown')
        return

    await update.message.reply_text("🔄 YİTX: YouTube videosu təhlil olunur və məzmunlar yenidən işlənilir...")
    output = repurpose_content(url)

    formatted_out = f"🎬 *YİTX Repurposing Nəticəsi:*\n\n{str(output)[:3500]}"
    await update.message.reply_text(formatted_out, parse_mode='Markdown')

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending = get_pending_scheduled_posts()
    if not pending:
        await update.message.reply_text("📭 Hazırda planlaşdırılmış və ya onay gözləyən post yoxdur.")
        return

    msg = "📋 *YİTX Planlaşdırılmış Postlar:*\n\n"
    for p in pending:
        msg += f"• *ID #{p['id']}*: {p['title'][:40]}... [{p['platforms']}] ({p['status']})\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    action, post_id = data.split("_")
    post_id = int(post_id)

    if action == "publish":
        update_post_status(post_id, "approved")
        await query.edit_message_caption(caption=f"✅ *Post #{post_id} təsdiqləndi və sosial medialara göndərilir...*", parse_mode='Markdown')
        from db.database import get_connection
        conn = get_connection()
        p = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        conn.close()
        if p:
            res = publish_to_platforms(p['content_text'], p['media_url'], p['platforms'])
            update_post_status(post_id, "published", error_log=str(res))
            await query.message.reply_text(f"🚀 Post #{post_id} uğurla yayımlandı!")

    elif action == "schedule":
        import datetime
        sched_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        update_post_status(post_id, "scheduled")
        await query.edit_message_caption(caption=f"📅 *Post #{post_id} 1 saat sonraya ({sched_time}) planlaşdırıldı!*", parse_mode='Markdown')

    elif action == "cancel":
        update_post_status(post_id, "cancelled")
        await query.edit_message_caption(caption=f"❌ *Post #{post_id} ləğv edildi.*", parse_mode='Markdown')

def main():
    init_db()
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in environment or master.env.")
        print("Please set TELEGRAM_BOT_TOKEN to launch YİTX Telegram Bot.")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("repurpose", repurpose_command))
    app.add_handler(CommandHandler("queue", queue_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), post_command))

    print("🤖 YİTX Telegram Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
