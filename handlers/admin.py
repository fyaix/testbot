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
    try:
        if len(context.args) != 2:
            raise ValueError()
        user_id = int(context.args[0])
        days = int(context.args[1])
        if db.fetchone("SELECT user_id FROM user_profiles WHERE user_id=?", (user_id,)):
            db.grant_pro(user_id, days)
            await update.message.reply_text(f"✅ Successfully granted {days} days of Pro to user `{user_id}`.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ User with ID `{user_id}` not found in the database.", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: `/grantpro <user_id> <days>`", parse_mode='Markdown')

@owner_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcasts a message to all users."""
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    all_users = db.get_all_user_ids()
    sent_count = 0
    failed_count = 0
    await update.message.reply_text(f"Starting broadcast to {len(all_users)} users...")

    for user_id in all_users:
        try:
            await context.bot.send_message(user_id, message)
            sent_count += 1
        except Exception:
            failed_count += 1

    await update.message.reply_text(f"Broadcast complete.\nSent: {sent_count}\nFailed: {failed_count}")

@owner_only
async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows bot statistics."""
    stats = db.get_stats()
    stats_text = f"""
    📊 **Bot Statistics** 📊

    - **Total Users:** {stats['total_users']}
    - **Pro Users:** {stats['pro_users']}
    - **Active Chats:** {stats['active_chats']}
    - **Reports (24h):** {stats['reports_24h']}
    """
    await update.message.reply_text(stats_text, parse_mode='Markdown')