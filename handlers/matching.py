from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db_instance as db
from config import states, GENDERS, HOBBIES
from .keyboards import MAIN_MENU, CHAT_MENU, GENDER_KEYBOARD, HOBBY_KEYBOARD

# --- Regular Find ---
async def find_partner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the regular partner search."""
    user_id = update.effective_user.id
    if db.is_in_chat(user_id):
        await update.message.reply_text("You are already in a chat. Use /next or /stop.", reply_markup=CHAT_MENU)
        return

    await update.message.reply_text("🔍 Searching for a random partner...")
    partner_id = db.find_partner(user_id)

    if partner_id:
        db.add_session(user_id, partner_id)
        await context.bot.send_message(user_id, "✅ Partner found! Start chatting.", reply_markup=CHAT_MENU)
        await context.bot.send_message(partner_id, "✅ You have a new chat partner!", reply_markup=CHAT_MENU)
    else:
        await update.message.reply_text("😔 No available partners found right now. Try again in a bit.", reply_markup=MAIN_MENU)

# --- Pro Search Conversation ---
async def search_pro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the pro search conversation."""
    user_id = update.effective_user.id
    if not db.is_pro(user_id):
        await update.message.reply_text("🚫 This is a Pro feature. /upgrade to get access.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    if not db.is_profile_complete(user_id):
        await update.message.reply_text("Your profile is incomplete. Please use /profile first.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    await update.message.reply_text("What gender are you looking for?", reply_markup=GENDER_KEYBOARD)
    return states["SEARCH_GENDER"]

async def search_gender_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the gender preference for pro search."""
    context.user_data['search_prefs'] = {'gender_pref': update.message.text}
    await update.message.reply_text("What hobby are you looking for?", reply_markup=HOBBY_KEYBOARD)
    return states["SEARCH_HOBBY"]

async def search_hobby_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the hobby preference for pro search."""
    context.user_data['search_prefs']['hobby_pref'] = update.message.text
    await update.message.reply_text("Enter the minimum age for your partner (e.g., 18).")
    return states["SEARCH_AGE_MIN"]

async def search_age_min_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the minimum age preference."""
    try:
        context.user_data['search_prefs']['age_min'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for age.")
        return states["SEARCH_AGE_MIN"]
    await update.message.reply_text("Enter the maximum age for your partner (e.g., 30).")
    return states["SEARCH_AGE_MAX"]

async def search_age_max_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles max age and executes the pro search."""
    try:
        context.user_data['search_prefs']['age_max'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for age.")
        return states["SEARCH_AGE_MAX"]

    user_id = update.effective_user.id
    prefs = context.user_data.pop('search_prefs')

    await update.message.reply_text(f"🔍 Searching for a partner with your preferences: {prefs}...")
    partner_id = db.find_partner(user_id, **prefs)

    if partner_id:
        db.add_session(user_id, partner_id)
        await context.bot.send_message(user_id, "✅ Partner found! Start chatting.", reply_markup=CHAT_MENU)
        await context.bot.send_message(partner_id, "✅ You have a new chat partner!", reply_markup=CHAT_MENU)
    else:
        await update.message.reply_text(
            "😔 **No partners found with your specific criteria.**\n\n"
            "You can try again, or use the regular `/find` command to search for any available partner.",
            reply_markup=MAIN_MENU,
            parse_mode='Markdown'
        )

    return ConversationHandler.END

# --- Chat Control ---
async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ends the current chat and starts a new search."""
    user_id = update.effective_user.id
    partner_id = db.end_session(user_id)
    if partner_id:
        await context.bot.send_message(partner_id, "Your partner has left the chat.", reply_markup=MAIN_MENU)
        await update.message.reply_text("Chat ended. Searching for a new partner...", reply_markup=MAIN_MENU)
        await find_partner_command(update, context) # Start a new search
    else:
        await update.message.reply_text("You are not in a chat.", reply_markup=MAIN_MENU)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ends the current chat."""
    user_id = update.effective_user.id
    partner_id = db.end_session(user_id)
    if partner_id:
        await context.bot.send_message(partner_id, "Your partner has ended the chat.", reply_markup=MAIN_MENU)
        await update.message.reply_text("Chat ended.", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("You are not in a chat.", reply_markup=MAIN_MENU)