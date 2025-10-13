from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import db_instance as db
from .keyboards import MAIN_MENU # We will create this file soon

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user_id = update.effective_user.id

    if not db.is_profile_complete(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Lengkapi Profil Sekarang", callback_data="complete_profile")],
            [InlineKeyboardButton("Lanjutkan & Cari Acak", callback_data="skip_profile")]
        ])
        await update.message.reply_text(
            "👋 **Selamat datang di Anonymous Chat!**\n\n"
            "Profilmu belum lengkap. Melengkapi profil akan memberikanmu pengalaman mencari partner yang lebih baik.",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        "👋 **Selamat datang kembali!**\n\n"
        "Gunakan menu di bawah atau ketik /help untuk melihat semua perintah yang tersedia.",
        reply_markup=MAIN_MENU
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the help message."""
    help_text = """
    📖 **Bantuan Bot Anonymous Chat** 📖

    **Perintah Utama:**
    • `/start` - Memulai bot atau kembali ke menu utama.
    • `/profile` - Mengatur atau memperbarui profil Anda (gender, usia, bio, foto, hobi).
    • `/find` - Mencari partner chat secara acak.
    • `/searchpro` - (Pro) Mencari partner dengan filter gender, hobi, dan usia.
    • `/next` - Menghentikan chat saat ini dan mencari partner baru.
    • `/stop` - Menghentikan chat saat ini.

    **Fitur Tambahan:**
    • `/playquiz` - Main kuis untuk mendapatkan poin atau akses Pro.
    • `/redeem` - Tukar poin dengan hari Pro.
    • `/joingroup` - Bergabung dengan grup chat anonim.
    • `/report` - Melaporkan partner Anda saat ini.
    • `/feedback` - Memberikan rating setelah sesi chat.
    • `/poll` - Membuat polling di dalam chat atau grup.
    • `/secretmode` - (Pro) Mengaktifkan mode pesan yang terhapus otomatis.

    **Perintah Admin (Owner Only):**
    • `/ban <user_id> <durasi_hari>`
    • `/unban <user_id>`
    • `/grantpro <user_id> <durasi_hari>`
    • `/broadcast <pesan>`
    • `/adminstats`
    """
    await update.message.reply_text(help_text, reply_markup=MAIN_MENU)

async def skip_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles when user decides to skip profile completion."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Baik, Anda bisa mencari partner acak sekarang. "
        "Jangan lupa untuk melengkapi profil nanti dengan perintah /profile.",
        reply_markup=MAIN_MENU
    )