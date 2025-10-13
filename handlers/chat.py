import logging
import requests
from telegram import Update
from telegram.ext import ContextTypes
from database import db_instance as db
from config import NSFW_API_KEY, NSFW_API_URL
from .keyboards import MAIN_MENU, CHAT_MENU

logger = logging.getLogger(__name__)

async def secret_mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggles secret mode for the current chat session."""
    user_id = update.effective_user.id
    session_info = db.fetchone("SELECT partner_id, secret_mode FROM sessions WHERE user_id=?", (user_id,))

    if not session_info:
        await update.message.reply_text("You must be in a chat to use this command.", reply_markup=MAIN_MENU)
        return

    partner_id, current_mode = session_info
    new_mode = not current_mode

    db.execute("UPDATE sessions SET secret_mode=? WHERE user_id IN (?, ?)", (int(new_mode), user_id, partner_id))

    if new_mode:
        await context.bot.send_message(user_id, "🤫 **Secret Mode Activated.** Messages will now be deleted after being sent.", reply_markup=CHAT_MENU)
        await context.bot.send_message(partner_id, "🤫 **Secret Mode Activated.** Your partner has enabled secret mode.", reply_markup=CHAT_MENU)
    else:
        await context.bot.send_message(user_id, "✅ **Secret Mode Deactivated.**", reply_markup=CHAT_MENU)
        await context.bot.send_message(partner_id, "✅ **Secret Mode Deactivated.**", reply_markup=CHAT_MENU)

def is_nsfw(file_url: str) -> bool:
    """Checks if an image is NSFW using the ModerateContent API."""
    if not NSFW_API_KEY:
        return False # Skip moderation if no API key is provided

    try:
        response = requests.get(NSFW_API_URL, params={"key": NSFW_API_KEY, "url": file_url})
        if response.ok:
            data = response.json()
            # The API returns a rating_label. 'everyone' is safe.
            return data.get("rating_label") != "everyone"
    except Exception as e:
        logger.error(f"NSFW API request failed: {e}")
        return False # Fail safe, assume it's not NSFW if API fails

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles all non-command messages and forwards them to the chat partner.
    This includes text, photos, videos, stickers, and voice messages.
    """
    user_id = update.effective_user.id

    # Check if the user is in a session
    session_info = db.fetchone("SELECT partner_id, secret_mode FROM sessions WHERE user_id=?", (user_id,))

    if not session_info:
        await update.message.reply_text(
            "You are not connected with anyone. Use the menu to find a partner.",
            reply_markup=MAIN_MENU
        )
        return

    partner_id, secret_mode = session_info
    message = update.message

    # --- Text Moderation ---
    if message.text:
        from config import MODERATION_WORDS
        if any(word.lower() in message.text.lower() for word in MODERATION_WORDS):
            await message.reply_text("⚠️ Your message contains inappropriate language and was not sent. Please be respectful.")
            # Optionally, log this to the owner
            # await context.bot.send_message(OWNER_ID, f"Moderation: User {user_id} used a banned word.")
            return

    try:
        if message.text:
            await context.bot.send_message(partner_id, message.text)
        elif message.photo:
            # --- Image Moderation ---
            file = await context.bot.get_file(message.photo[-1].file_id)
            if is_nsfw(file.file_path):
                await message.reply_text("🚫 Your image was detected as NSFW and was not sent.")
                # await context.bot.send_message(OWNER_ID, f"Moderation: NSFW image from {user_id} was blocked.")
                return
            await context.bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption)
        elif message.video:
            await context.bot.send_video(partner_id, message.video.file_id, caption=message.caption)
        elif message.voice:
            await context.bot.send_voice(partner_id, message.voice.file_id)
        elif message.sticker:
            await context.bot.send_sticker(partner_id, message.sticker.file_id)
        else:
            # Inform the user if the message type is not supported for forwarding
            await message.reply_text("This message type cannot be forwarded.")
            return

        # --- Secret Mode Logic ---
        if secret_mode:
            try:
                # Give it a moment to ensure the message is sent before deleting
                await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
            except Exception as e:
                logger.warning(f"Could not delete message {message.message_id} in secret mode: {e}")

    except Exception as e:
        logger.error(f"Failed to forward message from {user_id} to {partner_id}: {e}")
        # If the bot is blocked by the partner, end the chat for the current user
        if "bot was blocked by the user" in str(e).lower() or "forbidden" in str(e).lower():
            db.end_session(user_id)
            await update.message.reply_text(
                "❌ Your partner has blocked the bot. The chat has been ended.",
                reply_markup=MAIN_MENU
            )
        else:
            await update.message.reply_text("An error occurred while sending your message. Please try again.")