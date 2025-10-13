from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import db_instance as db
from config import OWNER_ID

def owner_only(func):
    """Decorator to restrict access to the owner."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("❌ This command is for the bot owner only.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def auto_update_profile(func):
    """Decorator to ensure user exists in DB and update username."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            # This can happen in some rare cases like channel posts
            return
        db.ensure_user_exists(user.id, user.username)
        return await func(update, context, *args, **kwargs)
    return wrapper

def check_ban_status(func):
    """Decorator to check if a user is banned before executing a command."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        banned_until = db.check_ban_status(update.effective_user.id)
        if banned_until:
            await update.message.reply_text(f"🚫 You are banned until {datetime.fromtimestamp(banned_until).strftime('%Y-%m-%d %H:%M')}.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper