import os
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

# Ambil token dari environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

# Supabase Config (jika Anda menggunakannya)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Admin ID
# Pastikan untuk mengubah string ke integer
ADMIN_ID_STR = os.getenv("ADMIN_ID")
try:
    ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR else None
except (ValueError, TypeError):
    ADMIN_ID = None

# Webhook URL (untuk deployment)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Konfigurasi Premium
PREMIUM_PRICE = os.getenv("PREMIUM_PRICE", "Rp 49,000")
PAYMENT_PROVIDER_TOKEN = os.getenv("YOUR_PAYMENT_PROVIDER_TOKEN")

# Fitur-fitur yang akan ditampilkan
PREMIUM_FEATURES = [
    "✅ Pencarian Tanpa Batas",
    "✅ Filter Gender & Minat",
    "✅ Prioritas Pencarian",
    "✅ Tanpa Iklan"
]