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
    """Starts the Pro Search conversation with inline buttons."""
    user_id = update.effective_user.id
    if not db.is_pro(user_id):
        await update.message.reply_text("🚫 This is a Pro feature. /upgrade to get access.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    if not db.is_profile_complete(user_id):
        await update.message.reply_text("Your profile is incomplete. Please use /profile first.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(gender, callback_data=f"searchgender_{gender}") for gender in GENDERS],
        [InlineKeyboardButton("Any Gender", callback_data="searchgender_Any")]
    ])
    await update.message.reply_text("Please select your preferred partner gender:", reply_markup=keyboard)
    return states["SEARCH_GENDER"]

async def search_gender_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the gender preference from the inline keyboard."""
    query = update.callback_query
    await query.answer()

    gender_pref = query.data.split('_')[1]
    context.user_data['search_prefs'] = {'gender_pref': gender_pref if gender_pref != "Any" else None}

    # Now ask for hobby
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(hobby, callback_data=f"searchhobby_{hobby}") for hobby in HOBBIES[:5]],
        [InlineKeyboardButton(hobby, callback_data=f"searchhobby_{hobby}") for hobby in HOBBIES[5:]],
        [InlineKeyboardButton("Any Hobby", callback_data="searchhobby_Any")]
    ])
    await query.edit_message_text("Now, select your preferred partner hobby:", reply_markup=keyboard)
    return states["SEARCH_HOBBY"]

async def search_hobby_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the hobby preference from the inline keyboard."""
    query = update.callback_query
    await query.answer()

    hobby_pref = query.data.split('_')[1]
    context.user_data['search_prefs']['hobby_pref'] = hobby_pref if hobby_pref != "Any" else None

    await query.edit_message_text("Great. Now, please send the desired age range for your partner.\n\nFormat: `min-max` (e.g., `18-25`)")
    return states["SEARCH_AGE_MIN"] # We'll just use one state for age range

async def search_age_range_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the age range input and executes the search."""
    try:
        age_min_str, age_max_str = update.message.text.split('-')
        age_min = int(age_min_str.strip())
        age_max = int(age_max_str.strip())
        if age_min >= age_max or age_min < 13:
            raise ValueError
        context.user_data['search_prefs']['age_min'] = age_min
        context.user_data['search_prefs']['age_max'] = age_max
    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please use `min-max` (e.g., `18-25`).",
            parse_mode='Markdown'
        )
        return states["SEARCH_AGE_MIN"] # Stay in the same state

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