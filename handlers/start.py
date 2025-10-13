from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from config import PREMIUM_PRICE, PREMIUM_FEATURES

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and the 'Back to Menu' button."""
    user = update.effective_user
    db.add_user(user.id, user.username)

    keyboard = [
        [InlineKeyboardButton("🔍 Cari Pasangan", callback_data='search')],
        [InlineKeyboardButton("💎 Premium", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ Bantuan", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"👋 Halo {user.first_name}!\n\n"
        "Selamat datang di Chat Anonim 1-on-1!\n\n"
        "🔍 Tekan tombol di bawah untuk mencari pasangan obrolan."
    )

    if update.callback_query:
        # If called from a button, edit the message
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        # If called by /start command, send a new message
        await update.message.reply_text(text, reply_markup=reply_markup)

async def myprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's current profile settings."""
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Silakan mulai bot dengan /start terlebih dahulu.")
        return

    # Prepare status texts
    premium_status = "✅ Aktif" if user.get('is_premium') else "❌ Tidak Aktif"
    gender = user.get('gender', 'Belum diatur').title()
    gender_preference = user.get('gender_preference', 'Siapa saja').title()
    interests = user.get('interests', 'Belum diatur')

    # Format interests for better readability
    if interests != 'Belum diatur':
        interests = ", ".join([i.strip() for i in interests.split(',')])

    text = f"""
👤 **Profil Anda**

**Status Premium:** {premium_status}
**Gender:** {gender}
**Mencari:** {gender_preference}
**Minat:** {interests}

Gunakan /settings untuk mengubah pengaturan ini.
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command and the help button."""
    help_text = f"""
🔹 **Cara Penggunaan:**
1. Tekan 🔍 Cari Pasangan
2. Tunggu bot mencarikan pasangan
3. Mulai chatting anonim!

🔹 **Perintah:**
/skip - Ganti pasangan
/stop - Akhiri obrolan
/report <alasan> - Laporkan pasangan
/settings - Atur profil & preferensi
/myprofile - Lihat profil Anda

🔹 **Premium ({PREMIUM_PRICE}/bulan):**"""

    for feature in PREMIUM_FEATURES:
        help_text += f"\n{feature}"

    help_text += "\n\n🔹 **Aturan:**\n- Hormati privasi orang lain\n- Tidak boleh spam\n- Tidak boleh mengirim konten ilegal"

    # Check if this is from a callback query or a message
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')