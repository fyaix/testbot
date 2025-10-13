import random
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db_instance as db
from .keyboards import get_quiz_reward_keyboard

QUIZ_QUESTIONS = [
    {"q": "What is the capital of Indonesia?", "a": "Jakarta"},
    {"q": "What is 2 + 5?", "a": "7"},
    {"q": "Who wrote the song 'Indonesia Raya'?", "a": "WR Supratman"},
]

async def play_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts a new quiz and stores it in the database."""
    quiz_id = random.randint(1000, 9999)
    question_data = random.choice(QUIZ_QUESTIONS)

    # Store quiz in database
    db.create_quiz(quiz_id, question_data["q"], question_data["a"].lower())

    # Store the current quiz_id in bot_data for global access if needed
    context.bot_data['active_quiz_id'] = quiz_id

    await update.message.reply_text(
        f"**Quiz #{quiz_id} is live!**\n\n"
        f"**Question:** {question_data['q']}\n\n"
        "Submit your answer with `/answer <your_answer>`",
        parse_mode='Markdown'
    )

async def answer_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles a user's answer to the currently active quiz."""
    user_id = update.effective_user.id
    quiz_id = context.bot_data.get('active_quiz_id')

    if not quiz_id:
        await update.message.reply_text("There is no active quiz right now. Wait for the next one!")
        return

    quiz = db.get_quiz(quiz_id)
    if not quiz:
        await update.message.reply_text("The active quiz seems to have ended. Wait for the next one!")
        return

    try:
        user_answer = " ".join(context.args).lower()
        if not user_answer:
            await update.message.reply_text("Please provide an answer. Usage: /answer <your_answer>")
            return
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide an answer. Usage: /answer <your_answer>")
        return

    if str(user_id) in quiz["winners"]:
        await update.message.reply_text("You have already won this quiz round!")
        return

    if len(quiz["winners"]) >= 5: # QUIZ_LIMIT_WINNERS
        await update.message.reply_text("Sorry, all the winner slots for this quiz have been taken.")
        return

    if user_answer == quiz["answer"]:
        # Add winner to both DBs (quiz and user profile)
        db.add_winner_to_quiz(quiz_id, user_id)
        db.add_quiz_winner(quiz_id, user_id) # This tracks who won which prize

        keyboard = get_quiz_reward_keyboard(quiz_id)
        await update.message.reply_text("🎉 Correct! You are a winner! Please choose your reward:", reply_markup=keyboard)
    else:
        await update.message.reply_text("❌ Incorrect answer. Try again!")

async def quiz_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's choice of quiz reward."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    try:
        _, reward_type, quiz_id_str = query.data.split('_')
        quiz_id = int(quiz_id_str)
    except (ValueError, IndexError):
        await query.edit_message_text("Invalid reward data.")
        return

    # A simple check to prevent claiming multiple times, though a DB check is better
    if "claimed" in context.user_data:
        await query.edit_message_text("You have already claimed a reward for this quiz.")
        return

    if reward_type == "pro":
        db.grant_pro_for_quiz(user_id, quiz_id, days=1)
        await query.edit_message_text("✅ Awesome! You now have Pro access for 1 day.")
    elif reward_type == "poin":
        db.grant_points_for_quiz(user_id, quiz_id, points=1)
        await query.edit_message_text("✅ Great! 1 point has been added to your account. Use /redeem to check.")

    context.user_data["claimed"] = True