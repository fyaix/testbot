from telegram import Update
from telegram.ext import ContextTypes
from database import db_instance as db
from .keyboards import get_report_keyboard, get_feedback_keyboard

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiates the report process against the current partner."""
    user_id = update.effective_user.id
    session_info = db.fetchone("SELECT partner_id FROM sessions WHERE user_id=?", (user_id,))

    if not session_info:
        await update.message.reply_text("You are not in a chat. You can only report a user during a chat.")
        return

    partner_id = session_info[0]
    keyboard = get_report_keyboard(partner_id)
    await update.message.reply_text("Please select a reason for the report or block the user directly:", reply_markup=keyboard)

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the report and block button presses."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data_parts = query.data.split('_')
    action = data_parts[0]

    if action == "report":
        reason = data_parts[1]
        session_info = db.fetchone("SELECT partner_id FROM sessions WHERE user_id=?", (user_id,))
        if not session_info:
            await query.edit_message_text("The chat session has already ended.")
            return

        reported_id = session_info[0]
        db.add_report(user_id, reported_id, reason)
        await query.edit_message_text(f"✅ Thank you. Your report for '{reason}' has been submitted.")
        # Notify owner
        # await context.bot.send_message(OWNER_ID, f"New report from {user_id} against {reported_id}. Reason: {reason}")

    elif action == "block":
        try:
            blocked_id = int(data_parts[1])
            db.execute("INSERT OR IGNORE INTO block_list (user_id, blocked_id) VALUES (?,?)", (user_id, blocked_id))
            await query.edit_message_text("✅ User has been blocked. You will not be matched with them again.")
        except (ValueError, IndexError):
            await query.edit_message_text("Error blocking user.")

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiates the feedback process."""
    user_id = update.effective_user.id
    if not db.is_in_chat(user_id):
        await update.message.reply_text("You can only give feedback during a chat.")
        return

    keyboard = get_feedback_keyboard()
    await update.message.reply_text("How would you rate your chat partner?", reply_markup=keyboard)

async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the feedback rating."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    rating = int(query.data.split('_')[1])

    session_info = db.fetchone("SELECT partner_id FROM sessions WHERE user_id=?", (user_id,))
    partner_id = session_info[0] if session_info else None

    # db.add_feedback(user_id, partner_id, rating, "") # Assuming a new DB method
    await query.edit_message_text(f"Thank you for your {rating}-star feedback!")