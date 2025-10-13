from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db_instance as db
from config import states, GENDERS, HOBBIES
from .keyboards import MAIN_MENU, GENDER_KEYBOARD, HOBBY_KEYBOARD

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the profile setup conversation."""
    await update.message.reply_text(
        "Let's set up your profile!\n\n"
        "First, what's your gender?",
        reply_markup=GENDER_KEYBOARD
    )
    return states["PROFILE_GENDER"]

async def gender_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the gender input."""
    gender = update.message.text
    if gender not in GENDERS:
        await update.message.reply_text("Invalid gender. Please choose from the options.", reply_markup=GENDER_KEYBOARD)
        return states["PROFILE_GENDER"]

    context.user_data['profile_data'] = {'gender': gender}
    await update.message.reply_text("Got it. How old are you?")
    return states["PROFILE_AGE"]

async def age_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the age input."""
    try:
        age = int(update.message.text)
        if not 13 <= age <= 99:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid age (e.g., 25).")
        return states["PROFILE_AGE"]

    context.user_data['profile_data']['age'] = age
    await update.message.reply_text("Great. Now, write a short bio about yourself.")
    return states["PROFILE_BIO"]

async def bio_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the bio input."""
    bio = update.message.text
    if len(bio) < 10:
        await update.message.reply_text("Your bio is too short. Please write a bit more.")
        return states["PROFILE_BIO"]

    context.user_data['profile_data']['bio'] = bio
    await update.message.reply_text("Looking good! Now, please send a profile photo.")
    return states["PROFILE_PHOTO"]

async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the profile photo input."""
    if not update.message.photo:
        await update.message.reply_text("That doesn't seem to be a photo. Please send a photo.")
        return states["PROFILE_PHOTO"]

    photo_id = update.message.photo[-1].file_id
    context.user_data['profile_data']['photo_id'] = photo_id
    await update.message.reply_text(
        "Awesome. Lastly, what are your hobbies? You can select multiple.",
        reply_markup=HOBBY_KEYBOARD
    )
    return states["PROFILE_HOBBY"]

async def hobby_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the hobby input and saves the complete profile."""
    hobbies = update.message.text
    hobby_list = [h.strip() for h in hobbies.split(',') if h.strip() in HOBBIES]

    if not hobby_list:
        await update.message.reply_text("Please select valid hobbies from the list.", reply_markup=HOBBY_KEYBOARD)
        return states["PROFILE_HOBBY"]

    context.user_data['profile_data']['hobbies'] = hobby_list

    # Save everything to the database
    user_id = update.effective_user.id
    profile_data = context.user_data.pop('profile_data', {})
    db.update_user_profile(user_id, profile_data)

    await update.message.reply_text(
        "✅ All set! Your profile has been updated. You can now find partners.",
        reply_markup=MAIN_MENU
    )
    return ConversationHandler.END

async def cancel_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the profile setup conversation."""
    context.user_data.pop('profile_data', None)
    await update.message.reply_text("Profile setup cancelled.", reply_markup=MAIN_MENU)
    return ConversationHandler.END