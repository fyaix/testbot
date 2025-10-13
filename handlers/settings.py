from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db

# Conversation states
GENDER, GENDER_PREFERENCE, INTERESTS = range(3)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the main settings menu."""
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    # Ensure the user exists
    if not user:
        await update.message.reply_text("Silakan mulai bot dengan /start terlebih dahulu.")
        return

    # Create status texts
    gender_status = user.get('gender', 'Belum diatur')
    pref_status = user.get('gender_preference', 'Siapa saja')
    interests_status = user.get('interests', 'Belum diatur')

    keyboard = [
        [InlineKeyboardButton(f"🚻 Gender Saya: {gender_status.title()}", callback_data='set_gender')],
        [InlineKeyboardButton(f"❤️ Preferensi: {pref_status.title()}", callback_data='set_gender_pref')],
        [InlineKeyboardButton(f"✨ Minat: {interests_status}", callback_data='set_interests')],
        [InlineKeyboardButton("« Kembali", callback_data='start_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ **Pengaturan Profil & Preferensi**\n\n"
        "Gunakan tombol di bawah untuk mengatur preferensi pencarian Anda. "
        "Fitur filter hanya aktif untuk pengguna Premium.",
        reply_markup=reply_markup
    )

# --- Gender Setup ---
async def set_gender_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks the user for their gender."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Laki-laki", callback_data='gender_male'), InlineKeyboardButton("Perempuan", callback_data='gender_female')],
        [InlineKeyboardButton("« Batal", callback_data='cancel_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Silakan pilih jenis kelamin Anda:", reply_markup=reply_markup)
    return GENDER

async def set_gender_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the user's gender."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    gender = query.data.split('_')[1]  # 'male' or 'female'

    db.update_user_preference(user_id, 'gender', gender)
    await query.edit_message_text(f"✅ Gender Anda telah disimpan sebagai: **{gender.title()}**")

    # Return to main settings menu or end conversation
    # For simplicity, we end here. A better UX would be to show the main settings menu again.
    return ConversationHandler.END

# --- Gender Preference Setup ---
async def set_gender_pref_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for gender preference."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Laki-laki", callback_data='pref_male'),
            InlineKeyboardButton("Perempuan", callback_data='pref_female')
        ],
        [InlineKeyboardButton("Siapa Saja", callback_data='pref_any')],
        [InlineKeyboardButton("« Batal", callback_data='cancel_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Anda ingin mencari pasangan:", reply_markup=reply_markup)
    return GENDER_PREFERENCE

async def set_gender_pref_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the gender preference."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    preference = query.data.split('_')[1] # 'male', 'female', or 'any'

    db.update_user_preference(user_id, 'gender_preference', preference)
    await query.edit_message_text(f"✅ Preferensi pencarian disimpan: **{preference.title()}**")
    return ConversationHandler.END

# --- Interests Setup ---
async def set_interests_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for user interests."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Masukkan minat Anda, pisahkan dengan koma (contoh: film, musik, game).\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    return INTERESTS

async def set_interests_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves user interests."""
    user_id = update.effective_user.id
    interests = update.message.text

    # Simple validation/cleanup
    interests_list = [i.strip().lower() for i in interests.split(',') if i.strip()]

    if not interests_list:
        await update.message.reply_text("Format tidak valid. Coba lagi.")
        return INTERESTS

    db.update_user_preference(user_id, 'interests', ','.join(interests_list))
    await update.message.reply_text(f"✅ Minat Anda telah disimpan: **{', '.join(interests_list)}**")
    return ConversationHandler.END

# --- General Conversation Handlers ---
async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the settings conversation."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Pengaturan dibatalkan.")
    else:
        await update.message.reply_text("Pengaturan dibatalkan.")
    return ConversationHandler.END