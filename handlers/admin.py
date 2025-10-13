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

@owner_only
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bans a user. Usage: /ban <user_id> <days>"""
    try:
        _, user_id_str, days_str = context.args
        user_id = int(user_id_str)
        days = int(days_str)
        duration_seconds = days * 86400
        db.ban_user(user_id, duration_seconds)
        await update.message.reply_text(f"User {user_id} has been banned for {days} days.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /ban <user_id> <days>")

@owner_only
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unbans a user. Usage: /unban <user_id>"""
    try:
        user_id = int(context.args[0])
        db.unban_user(user_id)
        await update.message.reply_text(f"User {user_id} has been unbanned.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /unban <user_id>")

@owner_only
async def grant_pro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grants pro access to a user. Usage: /grantpro <user_id> <days>"""
    # This would require a new DB method, let's assume it exists for now
    # db.grant_pro(user_id, days)
    await update.message.reply_text("This feature is not fully implemented yet.")

@owner_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcasts a message to all users."""
    # This requires getting all user IDs from the DB
    # all_users = db.get_all_user_ids()
    # message = " ".join(context.args)
    # for user_id in all_users:
    #     try:
    #         await context.bot.send_message(user_id, message)
    #     except Exception as e:
    #         print(f"Failed to send broadcast to {user_id}: {e}")
    await update.message.reply_text("This feature is not fully implemented yet.")

@owner_only
async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows bot statistics."""
    # This would require a new DB method to get stats
    # stats = db.get_stats()
    # await update.message.reply_text(f"Bot Stats:\n- Total Users: {stats['total_users']}\n- Active Chats: {stats['active_chats']}")
    await update.message.reply_text("This feature is not fully implemented yet.")