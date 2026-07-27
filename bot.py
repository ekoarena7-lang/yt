import os
import sys
import logging
import traceback
import re
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

def is_url(text):
    return bool(re.search(r"https?://[^\s]+", text))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 <b>YİTX Otomasyonu — AI Kontent Botuna Xoş Gəldiniz!</b>\n\n"
        "İstənilən <b>YouTube, Instagram Reels və ya TikTok video linkini</b> sadəcə bura göndərin!\n\n"
        "📌 <b>İstifadə:</b>\n"
        "• Link göndərin ➔ Avtomatik Repurpose edir (5 Shorts, 10 X post, LinkedIn məqaləsi).\n"
        "• <code>/post <konu></code> ➔ Mətn, şəkil və video hazırlayır.\n"
        "• <code>/queue</code> ➔ Planlaşdırılmış postlar növbəsi.\n"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💡 <b>YİTX Otomasyonu İstifadə Təlimatı:</b>\n\n"
        "1. Direct Link: YouTube, Instagram və ya TikTok linkini birbaşa çata atın.\n"
        "2. AI Mətn/Görsel: Mövzu yazın və ya <code>/post <mövzu></code> işlədin.\n"
        "3. Paylaşım: Təsdiqlə düyməsinə basaraq sosial medialara avto-paylaşın."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if user_text.startswith("/"):
        return

    if is_url(user_text):
        await repurpose_flow(update, user_text)
    else:
        await post_flow(update, user_text)

async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text("Lütfən bir mövzu qeyd edin. Məsələn: <code>/post AI biznes otomasyonu</code>", parse_mode='HTML')
        return

    if is_url(prompt):
        await repurpose_flow(update, prompt)
    else:
        await post_flow(update, prompt)

async def post_flow(update: Update, prompt: str):
    try:
        await update.message.reply_text("⏳ <b>YİTX AI:</b> Mətn və Görsel hazırlanır...", parse_mode='HTML')

        res_text = generate_ai_text(prompt)
        hook = res_text.get('hook', 'YİTX AI Post')
        caption_text = res_text.get('caption', '')
        hashtags = res_text.get('hashtags', '')
        
        full_caption = f"<b>{hook}</b>\n\n{caption_text}\n\n<i>{hashtags}</i>"
        media_url = generate_image(prompt)

        post_id = add_post(
            source_type='prompt',
            title=hook,
            content_text=f"{hook}\n\n{caption_text}\n\n{hashtags}",
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

        # Try sending photo; fallback to text if URL fails
        if media_url and media_url.startswith("http"):
            try:
                await update.message.reply_photo(
                    photo=media_url,
                    caption=f"📝 <b>YİTX AI Post (ID #{post_id}):</b>\n\n{full_caption}",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return
            except Exception as pe:
                print(f"Photo reply error fallback: {pe}")

        await update.message.reply_text(
            f"📝 <b>YİTX AI Post (ID #{post_id}):</b>\n\n{full_caption}\n\n🖼 <b>Media:</b> {media_url}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"Post flow error: {e}")
        traceback.print_exc()
        await update.message.reply_text(f"⚠️ <b>Xəta baş verdi:</b> {str(e)}", parse_mode='HTML')

async def repurpose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = " ".join(context.args) if context.args else ""
    if not url:
        await update.message.reply_text("Lütfən bir video linki qeyd edin. Məsələn: <code>/repurpose https://instagram.com/...</code>", parse_mode='HTML')
        return

    await repurpose_flow(update, url)

async def repurpose_flow(update: Update, url: str):
    try:
        await update.message.reply_text("🔄 <b>YİTX:</b> Video təhlil olunur və məzmunlar yenidən işlənilir...", parse_mode='HTML')
        output = repurpose_content(url)

        if isinstance(output, dict):
            hook = output.get("hook", "YİTX Video Repurpose")
            cap = output.get("caption", json.dumps(output, ensure_ascii=False, indent=2))
            tags = output.get("hashtags", "")
            out_str = f"<b>{hook}</b>\n\n{cap}\n\n<i>{tags}</i>"
        else:
            out_str = str(output)

        # Truncate if too long for Telegram
        if len(out_str) > 4000:
            out_str = out_str[:4000] + "..."

        await update.message.reply_text(
            f"🎬 <b>YİTX Repurposing Nəticəsi:</b>\n\n{out_str}",
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Repurpose flow error: {e}")
        traceback.print_exc()
        await update.message.reply_text(f"⚠️ <b>Repurposing Xətası:</b> {str(e)}", parse_mode='HTML')

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pending = get_pending_scheduled_posts()
        if not pending:
            await update.message.reply_text("📭 Hazırda planlaşdırılmış və ya onay gözləyən post yoxdur.")
            return

        msg = "📋 <b>YİTX Planlaşdırılmış Postlar:</b>\n\n"
        for p in pending:
            msg += f"• <b>ID #{p['id']}</b>: {p['title'][:40]}... [{p['platforms']}] ({p['status']})\n"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"⚠️ Xəta: {str(e)}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    action, post_id = data.split("_")
    post_id = int(post_id)

    if action == "publish":
        update_post_status(post_id, "approved")
        await query.edit_message_caption(caption=f"✅ <b>Post #{post_id} təsdiqləndi və yayımlanır...</b>", parse_mode='HTML')
        from db.database import get_connection
        conn = get_connection()
        p = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        conn.close()
        if p:
            res = publish_to_platforms(p['content_text'], p['media_url'], p['platforms'])
            update_post_status(post_id, "published", error_log=str(res))
            await query.message.reply_text(f"🚀 Post #{post_id} uğurla yayımlandı!", parse_mode='HTML')

    elif action == "schedule":
        import datetime
        sched_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        update_post_status(post_id, "scheduled")
        await query.edit_message_caption(caption=f"📅 <b>Post #{post_id} 1 saat sonraya ({sched_time}) planlaşdırıldı!</b>", parse_mode='HTML')

    elif action == "cancel":
        update_post_status(post_id, "cancelled")
        await query.edit_message_caption(caption=f"❌ <b>Post #{post_id} ləğv edildi.</b>", parse_mode='HTML')

def main():
    init_db()
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in environment or master.env.")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("repurpose", repurpose_command))
    app.add_handler(CommandHandler("queue", queue_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🤖 YİTX Telegram Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
