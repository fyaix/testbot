from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import GENDERS, HOBBIES, REPORT_REASONS

# --- Reply Keyboards ---
MAIN_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("🔍 Find Partner"), KeyboardButton("✨ Search Pro")],
    [KeyboardButton("👤 My Profile"), KeyboardButton("💎 Upgrade to Pro")],
    [KeyboardButton("🎮 Play Quiz"), KeyboardButton("👥 Join Group")],
], resize_keyboard=True)

CHAT_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("➡️ Next"), KeyboardButton("🛑 Stop")],
    [KeyboardButton("🌟 Feedback"), KeyboardButton("📊 Poll")],
    [KeyboardButton("🤫 Secret Mode")],
], resize_keyboard=True)

GROUP_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("👋 Leave Group"), KeyboardButton("📊 Poll")],
], resize_keyboard=True)

GENDER_KEYBOARD = ReplyKeyboardMarkup([GENDERS], one_time_keyboard=True, resize_keyboard=True)
HOBBY_KEYBOARD = ReplyKeyboardMarkup([HOBBIES], one_time_keyboard=True, resize_keyboard=True)


# --- Inline Keyboards ---
def get_report_keyboard(partner_id):
    """Generates the report/block keyboard."""
    buttons = [
        [InlineKeyboardButton(reason, callback_data=f"report_{reason}")] for reason in REPORT_REASONS
    ]
    buttons.append([InlineKeyboardButton("🚫 Block User", callback_data=f"block_{partner_id}")])
    return InlineKeyboardMarkup(buttons)

def get_feedback_keyboard():
    """Generates the feedback rating keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐️", callback_data="fb_1"),
            InlineKeyboardButton("⭐️⭐️", callback_data="fb_2"),
            InlineKeyboardButton("⭐️⭐️⭐️", callback_data="fb_3"),
        ],
        [
            InlineKeyboardButton("⭐️⭐️⭐️⭐️", callback_data="fb_4"),
            InlineKeyboardButton("⭐️⭐️⭐️⭐️⭐️", callback_data="fb_5"),
        ]
    ])

def get_quiz_reward_keyboard(quiz_id):
    """Generates the quiz reward selection keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 Pro 1 Hari", callback_data=f"quizpro_{quiz_id}"),
            InlineKeyboardButton("🪙 1 Poin", callback_data=f"quizpoin_{quiz_id}")
        ]
    ])