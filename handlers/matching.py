import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import db

logger = logging.getLogger(__name__)

async def search_partner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the search for a chat partner, including daily limit checks."""
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        message = update.callback_query.message
    else:
        user_id = update.effective_user.id
        message = update.message

    # Check if user is already in a chat
    user_status = db.get_user_status(user_id)
    if user_status:
        if user_status['status'] == 'chatting':
            await message.reply_text("❌ Anda sedang dalam obrolan. Gunakan /skip untuk ganti pasangan.")
            return
        elif user_status['status'] == 'searching':
            await message.reply_text("⏳ Anda sudah dalam antrean pencarian.")
            return

    # Check daily limit for non-premium users
    can_search, remaining = db.check_and_reset_daily_limit(user_id)
    if not can_search:
        premium_button = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade ke Premium", callback_data='premium')]])
        await message.reply_text(
            "🚫 **Batas Pencarian Harian Tercapai**\n\n"
            "Anda telah menggunakan 100 pencarian gratis hari ini. "
            "Coba lagi besok atau upgrade ke Premium untuk pencarian tanpa batas!",
            reply_markup=premium_button
        )
        return

    # If allowed, proceed with search
    db.set_user_status(user_id, 'searching')
    db.increment_search_count(user_id)

    remaining_text = f"(Sisa pencarian hari ini: {remaining - 1})" if remaining != -1 else "(Pencarian Tanpa Batas)"
    await message.reply_text(f"🔍 Mencari pasangan... {remaining_text}")

    # Get user's data for filtering
    user = db.get_user(user_id)
    is_premium = user.get('is_premium', False)

    # Premium users can use filters, but they must set their own gender first
    if is_premium and not user.get('gender'):
        await message.reply_text(
            "⚠️ Untuk menggunakan filter, Anda harus mengatur gender Anda terlebih dahulu di /settings.",
        )
        # Reset status because the search cannot proceed
        db.set_user_status(user_id, 'idle')
        return

    available_users = db.get_searching_users(
        user_id=user_id,
        is_premium=is_premium,
        gender_preference=user.get('gender_preference', 'any'),
        user_gender=user.get('gender'),
        interests=user.get('interests')
    )

    if available_users:
        partner_id = available_users[0]

        db.set_user_status(user_id, 'chatting', partner_id)
        db.set_user_status(partner_id, 'chatting', user_id)

        db.create_session(user_id, partner_id)

        common_text = ("✅ Pasangan ditemukan! Silakan mulai chatting.\n\n"
                       "⚠️ Ingat: Tetap sopan dan jangan berbagi informasi pribadi.\n\n"
                       "Gunakan /skip untuk ganti pasangan atau /stop untuk berhenti.")

        await context.bot.send_message(chat_id=user_id, text=common_text)
        await context.bot.send_message(chat_id=partner_id, text=common_text)
    else:
        await message.reply_text("⏳ Belum ada pasangan yang tersedia. Anda akan dihubungkan saat ada yang mencari.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forwards messages between connected users."""
    user_id = update.effective_user.id
    user_data = db.get_user_status(user_id)

    if not user_data or user_data['status'] != 'chatting':
        await update.message.reply_text("❌ Anda tidak sedang dalam obrolan. Gunakan /search untuk mencari pasangan.")
        return

    partner_id = user_data['partner_id']
    if not partner_id:
        await update.message.reply_text("❌ Pasangan tidak ditemukan. Mungkin mereka telah pergi. Coba cari lagi dengan /search.")
        db.set_user_status(user_id, 'idle')
        return

    try:
        await context.bot.forward_message(
            chat_id=partner_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error forwarding message from {user_id} to {partner_id}: {e}")
        # If partner blocked the bot, end the chat
        if "bot was blocked by the user" in str(e):
            await update.message.reply_text("❌ Gagal mengirim pesan. Pasangan Anda mungkin telah memblokir bot. Obrolan diakhiri.")
            db.end_chat(user_id)
        else:
            await update.message.reply_text("❌ Gagal mengirim pesan. Coba lagi nanti.")

async def end_chat_session(context: ContextTypes.DEFAULT_TYPE, user_id: int, partner_id: int, user_message: str, partner_message: str):
    """A helper function to end a chat session and notify both users."""
    db.end_chat(user_id)

    if partner_id:
        try:
            await context.bot.send_message(chat_id=partner_id, text=partner_message)
        except Exception as e:
            logger.error(f"Error notifying partner {partner_id} during chat end: {e}")

    await context.bot.send_message(chat_id=user_id, text=user_message)

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /skip command."""
    user_id = update.effective_user.id
    user_data = db.get_user_status(user_id)

    if not user_data or user_data['status'] != 'chatting':
        await update.message.reply_text("❌ Anda tidak sedang dalam obrolan.")
        return

    partner_id = user_data['partner_id']
    if not partner_id:
        await update.message.reply_text("❌ Pasangan tidak ditemukan.")
        return

    await update.message.reply_text("🚶 Anda meninggalkan obrolan. Mencari pasangan baru...")

    # End the current chat and start a new search
    db.end_chat(user_id)
    if partner_id:
        try:
            await context.bot.send_message(chat_id=partner_id, text="🚶 Pasangan Anda telah meninggalkan obrolan.")
        except Exception as e:
            logger.error(f"Error notifying partner {partner_id} about skip: {e}")

    await search_partner(update, context)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /stop command."""
    user_id = update.effective_user.id
    user_data = db.get_user_status(user_id)

    if not user_data or user_data['status'] != 'chatting':
        await update.message.reply_text("❌ Anda tidak sedang dalam obrolan.")
        return

    partner_id = db.end_chat(user_id)

    user_message = "🛑 Obrolan diakhiri. Ketik /start untuk mencari pasangan baru."
    partner_message = "🛑 Obrolan telah diakhiri oleh pasangan Anda."

    await end_chat_session(context, user_id, partner_id, user_message, partner_message)