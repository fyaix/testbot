from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from config import PREMIUM_PRICE, PREMIUM_FEATURES, PAYMENT_PROVIDER_TOKEN

async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays information about premium features."""
    keyboard = [
        [InlineKeyboardButton("💎 Upgrade ke Premium", callback_data='upgrade_premium')],
        [InlineKeyboardButton("« Kembali", callback_data='start_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    features_text = "\n".join(PREMIUM_FEATURES)

    text = f"""
💎 **UPGRADE KE PREMIUM** 💎

Nikmati pengalaman terbaik dengan fitur eksklusif:

{features_text}

💰 **Harga:** {PREMIUM_PRICE}/bulan

Upgrade sekarang untuk menemukan koneksi yang lebih berarti!
"""

    # Check if this is from a callback query or a message
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a payment invoice to the user."""
    chat_id = update.effective_chat.id
    title = "Langganan Premium 1 Bulan"
    description = "Akses semua fitur premium selama 30 hari."
    payload = "premium-monthly-payload"
    currency = "IDR"

    # Harga dalam satuan terkecil (misal: Rupiah, bukan 49.000)
    # Hapus pemisah ribuan dan konversi ke integer
    price_str = PREMIUM_PRICE.replace("Rp", "").replace(",", "").replace(".", "").strip()
    price = int(price_str) * 100 # Jika menggunakan payment gateway yang butuh sen

    if not PAYMENT_PROVIDER_TOKEN:
        await context.bot.send_message(chat_id, "Maaf, pembayaran saat ini sedang tidak tersedia. Silakan coba lagi nanti.")
        return

    await context.bot.send_invoice(
        chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency=currency,
        prices=[LabeledPrice(title, price)]
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles pre-checkout queries."""
    query = update.pre_checkout_query
    # Here you can check the payload and other details
    if query.invoice_payload != 'premium-monthly-payload':
        await query.answer(ok=False, error_message="Terjadi kesalahan. Silakan coba lagi.")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles successful payments."""
    user_id = update.effective_user.id

    # Update user status to premium in the database for 30 days
    db.set_premium_status(user_id, days=30)

    await update.message.reply_text(
        "✅ **Pembayaran Berhasil!**\n\n"
        "Selamat! Akun Anda telah di-upgrade ke Premium.\n"
        "Semua fitur premium kini telah aktif selama 30 hari. Selamat menikmati!"
    )