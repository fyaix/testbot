import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)
from config import BOT_TOKEN, ADMIN_ID, WEBHOOK_URL, PREMIUM_PRICE, PREMIUM_FEATURES
from database import db

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# BASIC COMMANDS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.add_user(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("🔍 Cari Pasangan", callback_data='search')],
        [InlineKeyboardButton("💎 Premium", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ Bantuan", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Halo {user.first_name}!\n\n"
        "Selamat datang di Chat Anonim 1-on-1!\n\n"
        "🔍 Tekan tombol di bawah untuk mencari pasangan obrolan.",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = f"""
🔹 **Cara Penggunaan:**
1. Tekan 🔍 Cari Pasangan
2. Tunggu bot mencarikan pasangan
3. Mulai chatting anonim!

🔹 **Perintah:**
/skip - Ganti pasangan
/stop - Akhiri obrolan
/report <alasan> - Laporkan pasangan

🔹 **Premium ({PREMIUM_PRICE}/bulan):"""
    
    for feature in PREMIUM_FEATURES:
        help_text += f"\n{feature}"
    
    help_text += "\n\n🔹 **Aturan:**\n- Hormati privasi orang lain\n- Tidak boleh spam\n- Tidak boleh mengirim konten ilegal"
    
    # Periksa apakah ini dari callback query atau message
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')

# ======================
# MATCHING SYSTEM
# ======================
async def search_partner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Dapatkan user_id dari update
    if update.callback_query:
        user_id = update.callback_query.from_user.id
    else:
        user_id = update.effective_user.id
    
    # Cek status user
    user_data = db.get_user_status(user_id)
    if user_data:
        if user_data['status'] == 'chatting':
            if update.callback_query:
                await update.callback_query.message.reply_text("❌ Anda sedang dalam obrolan. Gunakan /skip untuk ganti pasangan.")
            else:
                await update.message.reply_text("❌ Anda sedang dalam obrolan. Gunakan /skip untuk ganti pasangan.")
            return
        elif user_data['status'] == 'searching':
            if update.callback_query:
                await update.callback_query.message.reply_text("⏳ Sedang mencari pasangan...")
            else:
                await update.message.reply_text("⏳ Sedang mencari pasangan...")
            return
    
    # Set status ke searching
    db.set_user_status(user_id, 'searching')
    
    if update.callback_query:
        await update.callback_query.message.reply_text("🔍 Mencari pasangan... Mohon tunggu.")
    else:
        await update.message.reply_text("🔍 Mencari pasangan... Mohon tunggu.")
    
    # Cari pasangan yang tersedia
    available_users = db.get_searching_users(exclude_user_id=user_id)
    
    if available_users:
        partner_id = available_users[0]
        
        # Hubungkan kedua user
        db.set_user_status(user_id, 'chatting', partner_id)
        db.set_user_status(partner_id, 'chatting', user_id)
        
        # Log session
        db.cursor.execute("""
        INSERT INTO sessions (user1_id, user2_id, started_at)
        VALUES (?, ?, ?)
        """, (user_id, partner_id, datetime.now()))
        db.conn.commit()
        
        # Beritahu kedua user
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Pasangan ditemukan! Silakan mulai chatting.\n\n"
                 "⚠️ Ingat: Tetap sopan dan jangan berbagi informasi pribadi.\n\n"
                 "Gunakan /skip untuk ganti pasangan atau /stop untuk berhenti."
        )
        
        await context.bot.send_message(
            chat_id=partner_id,
            text="✅ Pasangan ditemukan! Silakan mulai chatting.\n\n"
                 "⚠️ Ingat: Tetap sopan dan jangan berbagi informasi pribadi.\n\n"
                 "Gunakan /skip untuk ganti pasangan atau /stop untuk berhenti."
        )
    else:
        if update.callback_query:
            await update.callback_query.message.reply_text("⏳ Belum ada pasangan yang tersedia. Anda akan dihubungkan saat ada yang mencari.")
        else:
            await update.message.reply_text("⏳ Belum ada pasangan yang tersedia. Anda akan dihubungkan saat ada yang mencari.")

# ======================
# MESSAGE HANDLING
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = db.get_user_status(user_id)
    
    if not user_data or user_data['status'] != 'chatting':
        await update.message.reply_text("❌ Anda tidak sedang dalam obrolan. Gunakan /search untuk mencari pasangan.")
        return
    
    partner_id = user_data['partner_id']
    if not partner_id:
        await update.message.reply_text("❌ Pasangan tidak ditemukan.")
        return
    
    # Forward pesan ke partner
    try:
        await context.bot.forward_message(
            chat_id=partner_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        await update.message.reply_text("❌ Gagal mengirim pesan. Coba lagi nanti.")

# ======================
# CHAT CONTROL
# ======================
async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = db.get_user_status(user_id)
    
    if not user_data or user_data['status'] != 'chatting':
        await update.message.reply_text("❌ Anda tidak sedang dalam obrolan.")
        return
    
    partner_id = user_data['partner_id']
    if not partner_id:
        await update.message.reply_text("❌ Pasangan tidak ditemukan.")
        return
    
    # Akhiri chat dengan partner saat ini
    db.end_chat(user_id)
    
    # Beritahu partner
    try:
        await context.bot.send_message(
            chat_id=partner_id,
            text="🚶 Pasangan Anda telah meninggalkan obrolan."
        )
    except Exception as e:
        logger.error(f"Error notifying partner: {e}")
    
    # Cari pasangan baru
    await search_partner(update, context)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    partner_id = db.end_chat(user_id)
    
    if partner_id:
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text="🛑 Obrolan telah diakhiri oleh pasangan Anda."
            )
        except Exception as e:
            logger.error(f"Error notifying partner: {e}")
    
    await update.message.reply_text("🛑 Obrolan diakhiri. Ketik /search untuk mencari pasangan baru.")

# ======================
# REPORT SYSTEM
# ======================
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = db.get_user_status(user_id)
    
    if not user_data or user_data['status'] != 'chatting':
        await update.message.reply_text("❌ Anda tidak sedang dalam obrolan.")
        return
    
    partner_id = user_data['partner_id']
    if not partner_id:
        await update.message.reply_text("❌ Pasangan tidak ditemukan.")
        return
    
    reason = " ".join(context.args) if context.args else "Tidak ada alasan"
    
    # Simpan laporan
    db.add_report(user_id, partner_id, reason)
    
    # Beritahu admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🚨 LAPORAN BARU 🚨\n"
             f"Pelapor: {user_id}\n"
             f"Terlapor: {partner_id}\n"
             f"Alasan: {reason}"
    )
    
    await update.message.reply_text("✅ Laporan Anda telah diterima. Terima kasih!")

# ======================
# PREMIUM SYSTEM
# ======================
async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("💎 Upgrade ke Premium", callback_data='upgrade_premium')],
        [InlineKeyboardButton("❌ Kembali", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"💎 **PREMIUM FEATURES**\n\n"
    for feature in PREMIUM_FEATURES:
        text += f"{feature}\n"
    
    text += f"\n💰 Harga: {PREMIUM_PRICE}/bulan\n\n"
    text += "Dapatkan pengalaman chatting terbaik!"
    
    # Periksa apakah ini dari callback query atau message
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    title = "Premium 1 Bulan"
    description = "Akses semua fitur premium"
    payload = "premium-monthly"
    provider_token = "YOUR_PAYMENT_PROVIDER_TOKEN"  # Dari @BotFather
    currency = "USD"
    price = 299  # $2.99
    
    await context.bot.send_invoice(
        chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token=provider_token,
        currency=currency,
        prices=[LabeledPrice("Premium 1 Bulan", price)]
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query.invoice_payload != 'premium-monthly':
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "✅ Pembayaran berhasil!\n\n"
        "Fitur premium Anda telah aktif.\n"
        "Selamat menikmati pengalaman chatting terbaik!"
    )
    # Di sini update status user di database

# ======================
# BUTTON HANDLERS
# ======================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'search':
        await search_partner(update, context)
    elif query.data == 'help':
        await help_command(update, context)
    elif query.data == 'premium':
        await premium_info(update, context)
    elif query.data == 'upgrade_premium':
        await send_invoice(update, context)
    elif query.data == 'back':
        await start(update, context)

# ======================
# ADMIN PANEL
# ======================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Statistik", callback_data='admin_stats')],
        [InlineKeyboardButton("🚨 Laporan", callback_data='admin_reports')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 **Admin Panel**\n\nPilih aksi:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    
    stats = db.get_stats()
    
    text = f"📊 **STATISTIK BOT**\n\n"
    text += f"👥 Total Users: {stats['total_users']}\n"
    text += f"💬 Active Chats: {stats['active_users']}\n"
    text += f"🔗 Total Sessions: {stats['total_sessions']}\n"
    text += f"🚨 Total Reports: {stats['total_reports']}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    
    reports = db.get_reports(5)
    
    if not reports:
        await update.message.reply_text("✅ Tidak ada laporan baru")
        return
    
    text = "🚨 **DAFTAR LAPORAN**\n\n"
    for report in reports:
        text += f"🆔 ID: {report[0]}\n"
        text += f"👤 Pelapor: {report[1]}\n"
        text += f"👤 Terlapor: {report[2]}\n"
        text += f"📝 Alasan: {report[3]}\n"
        text += f"⏰ {report[4]}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ======================
# MAIN FUNCTION
# ======================
def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("skip", skip_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    # Button handlers
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    if WEBHOOK_URL:
        # For production (Vercel/Cloudflare Workers)
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            url_path=BOT_TOKEN,
            webhook_url=WEBHOOK_URL + BOT_TOKEN
        )
    else:
        # For local development
        application.run_polling()

if __name__ == '__main__':
    main()
