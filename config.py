import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Main Bot Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables. Please check your .env file.")

OWNER_ID_STR = os.getenv("OWNER_ID")
try:
    OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR else None
except (ValueError, TypeError):
    print("Warning: OWNER_ID is not a valid integer. Some owner-only commands may not work.")
    OWNER_ID = None

DB_PATH = "bot_database.db"

# --- Feature-specific Configuration ---
NSFW_API_KEY = os.getenv("NSFW_API_KEY")
NSFW_API_URL = "https://api.moderatecontent.com/moderate/"
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")

# --- Static Lists & Constants ---
LANGS = ["English", "Indonesian"]
GENDERS = ["Male", "Female", "Other"]
HOBBIES = ["Music", "Sports", "Gaming", "Travel", "Reading", "Cooking", "Drawing", "Coding", "Photography", "Other"]
MODERATION_WORDS = ["anjing", "babi", "kontol", "bangsat", "memek", "ngentot"]
REPORT_REASONS = ["Spam", "SARA", "Pornografi", "Kata Kasar", "Penipuan", "Lainnya"]

# --- Game & Pricing Constants ---
PRO_WEEK_PRICE = 1000  # Example price
PRO_MONTH_PRICE = 3500 # Example price
QUIZ_LIMIT_WINNERS = 5

# --- Conversation States ---
# Using a dictionary for clarity and to avoid state collisions
states = {
    "PROFILE_GENDER": 1,
    "PROFILE_AGE": 2,
    "PROFILE_BIO": 3,
    "PROFILE_PHOTO": 4,
    "PROFILE_LANG": 5,
    "PROFILE_HOBBY": 6,
    "SEARCH_TYPE": 7,
    "SEARCH_GENDER": 8,
    "SEARCH_HOBBY": 9,
    "SEARCH_AGE_MIN": 10,
    "SEARCH_AGE_MAX": 11,
    "QUIZ_ANSWER": 12
}