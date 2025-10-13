from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import db

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the admin panel."""
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
    """Shows bot statistics to the admin."""
    if update.effective_user.id != ADMIN_ID:
        return

    stats = db.get_stats()

    text = f"""📊 **STATISTIK BOT**

👥 Total Pengguna: {stats['total_users']}
💬 Pengguna Aktif (Chatting): {stats['active_users']}
🔄 Total Sesi: {stats['total_sessions']}
🚨 Total Laporan: {stats['total_reports']}"""

    await update.callback_query.message.reply_text(text, parse_mode='Markdown')

async def admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the latest reports to the admin."""
    if update.effective_user.id != ADMIN_ID:
        return

    reports = db.get_reports(5)

    if not reports:
        await update.callback_query.message.reply_text("✅ Tidak ada laporan baru.")
        return

    text = "🚨 **DAFTAR LAPORAN TERBARU**\n\n"
    for report in reports:
        text += f"🆔 ID: {report[0]}\n"
        text += f"👤 Pelapor: `{report[1]}`\n"
        text += f"👤 Terlapor: `{report[2]}`\n"
        text += f"📝 Alasan: {report[3]}\n"
        text += f"⏰ Waktu: {report[4]}\n\n"

    await update.callback_query.message.reply_text(text, parse_mode='Markdown')

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /report command."""
    user_id = update.effective_user.id
    user_data = db.get_user_status(user_id)

    if not user_data or user_data['status'] != 'chatting':
        await update.message.reply_text("❌ Anda hanya bisa melaporkan saat sedang dalam obrolan.")
        return

    partner_id = user_data['partner_id']
    if not partner_id:
        await update.message.reply_text("❌ Pasangan tidak ditemukan.")
        return

    reason = " ".join(context.args) if context.args else "Tidak ada alasan yang diberikan"

    db.add_report(user_id, partner_id, reason)

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🚨 **LAPORAN BARU** 🚨\n"
             f"**Pelapor:** `{user_id}`\n"
             f"**Terlapor:** `{partner_id}`\n"
             f"**Alasan:** {reason}",
        parse_mode='Markdown'
    )

    await update.message.reply_text("✅ Laporan Anda telah kami terima. Tim kami akan meninjaunya. Terima kasih.")