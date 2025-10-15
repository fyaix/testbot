from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db_instance as db
from config import states, GENDERS, HOBBIES
from .keyboards import MAIN_MENU, CHAT_MENU, GENDER_KEYBOARD, HOBBY_KEYBOARD

# --- Regular Find ---
async def find_partner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the regular partner search, now with profile preview."""
    user_id = update.effective_user.id
    user_status = db.get_user_status(user_id)

    if user_status and user_status['status'] in ['in_chat', 'proposing']:
        await update.message.reply_text("You are already in a chat or have a pending proposal.", reply_markup=CHAT_MENU)
        return

    db.set_user_status(user_id, 'searching')
    await update.message.reply_text("🔍 Searching for a random partner...")

    partner_id = db.find_partner(user_id)

    if partner_id:
        # Found a partner, now send a proposal instead of starting chat
        db.set_user_status(user_id, 'proposing', proposed_to=partner_id)
        db.set_user_status(partner_id, 'being_proposed', proposed_to=user_id)

        partner_profile = db.get_profile(partner_id)

        preview_text = (
            "**Partner Found!**\n\n"
            f"**Age:** {partner_profile.get('age', 'N/A')}\n"
            f"**Gender:** {partner_profile.get('gender', 'N/A')}\n"
            f"**Bio:** {partner_profile.get('bio', 'No bio provided.')}\n\n"
            "Do you want to start a chat with this person?"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"proposal_accept_{partner_id}"),
                InlineKeyboardButton("❌ Skip", callback_data=f"proposal_skip_{partner_id}")
            ]
        ])

        sent_message = await context.bot.send_message(user_id, preview_text, reply_markup=keyboard, parse_mode='Markdown')

        # Schedule a job to timeout the proposal
        context.job_queue.run_once(
            timeout_proposal,
            60, # 60 seconds
            data={'user_id': user_id, 'partner_id': partner_id, 'message_id': sent_message.message_id},
            name=f"proposal_timeout_{user_id}_{partner_id}"
        )
    else:
        await update.message.reply_text("😔 No available partners found right now. You are in the queue.", reply_markup=MAIN_MENU)

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

    db.set_user_status(user_id, 'searching')
    partner_id = db.find_partner(user_id, **prefs)

    if partner_id:
        db.set_user_status(user_id, 'proposing', proposed_to=partner_id)
        db.set_user_status(partner_id, 'being_proposed', proposed_to=user_id)

        partner_profile = db.get_profile(partner_id)

        preview_text = (
            "**Partner Found!**\n\n"
            f"**Age:** {partner_profile.get('age', 'N/A')}\n"
            f"**Gender:** {partner_profile.get('gender', 'N/A')}\n"
            f"**Bio:** {partner_profile.get('bio', 'No bio provided.')}\n\n"
            "Do you want to start a chat with this person?"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"proposal_accept_{partner_id}"),
                InlineKeyboardButton("❌ Skip", callback_data=f"proposal_skip_{partner_id}")
            ]
        ])

        sent_message = await context.bot.send_message(user_id, preview_text, reply_markup=keyboard, parse_mode='Markdown')

        # Schedule a job to timeout the proposal
        context.job_queue.run_once(
            timeout_proposal,
            60, # 60 seconds
            data={'user_id': user_id, 'partner_id': partner_id, 'message_id': sent_message.message_id},
            name=f"proposal_timeout_{user_id}_{partner_id}"
        )
    else:
        await update.message.reply_text(
            "😔 **No partners found with your specific criteria.**\n\n"
            "You can try again, or use the regular `/find` command to search for any available partner.",
            reply_markup=MAIN_MENU,
            parse_mode='Markdown'
        )
        db.set_user_status(user_id, 'idle') # Reset status if no partner found

    return ConversationHandler.END

async def proposal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Accept' or 'Skip' action on a profile proposal."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    action, partner_id_str = query.data.split('_')[1:]
    partner_id = int(partner_id_str)

    # Verify the user is in the correct state
    user_status = db.get_user_status(user_id)
    if not user_status or user_status['status'] != 'proposing' or user_status['proposed_to'] != partner_id:
        await query.edit_message_text("This proposal is no longer valid.")
        return

    # Remove the timeout job as the user has responded
    current_jobs = context.job_queue.get_jobs_by_name(f"proposal_timeout_{user_id}_{partner_id}")
    for job in current_jobs:
        job.schedule_removal()

    if action == "accept":
        # Both users are now in chat
        db.set_user_status(user_id, 'in_chat')
        db.set_user_status(partner_id, 'in_chat')
        db.add_session(user_id, partner_id)

        await query.edit_message_text("✅ **Connection established!** You can start chatting now.", reply_markup=None)
        await context.bot.send_message(partner_id, "✅ **You have a new chat partner!**", reply_markup=CHAT_MENU)

    elif action == "skip":
        # Reset both users' status
        db.set_user_status(user_id, 'idle')
        db.set_user_status(partner_id, 'idle')

        await query.edit_message_text("Skipped. Searching for a new partner...", reply_markup=None)
        # Immediately start a new search for the user
        await find_partner_command(query, context)

async def timeout_proposal(context: ContextTypes.DEFAULT_TYPE):
    """Cancels a proposal if the user doesn't respond in time."""
    job = context.job
    user_id = job.data['user_id']
    partner_id = job.data['partner_id']

    user_status = db.get_user_status(user_id)
    # Only cancel if the user is still in the 'proposing' state
    if user_status and user_status['status'] == 'proposing' and user_status['proposed_to'] == partner_id:
        db.set_user_status(user_id, 'idle')
        db.set_user_status(partner_id, 'idle')

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=job.data['message_id'],
            text="Proposal expired. Searching again..."
        )
        # Re-trigger the search
        # We need to find a way to pass the original update object or create a mock one
        # For now, we'll just send a message
        await context.bot.send_message(user_id, "Please press 'Find Partner' again.", reply_markup=MAIN_MENU)

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