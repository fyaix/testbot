from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes
from config import PAYMENT_PROVIDER_TOKEN, PRO_MONTH_PRICE

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the payment process for Pro subscription."""
    chat_id = update.message.chat.id
    title = "Pro Subscription (30 Days)"
    description = "Unlock all pro features like advanced search, unlimited chats, and more for 30 days."
    payload = "pro-month-payload"
    currency = "USD" # Or your preferred currency
    price = PRO_MONTH_PRICE # This should be in the smallest unit of the currency (e.g., cents)

    if not PAYMENT_PROVIDER_TOKEN:
        await update.message.reply_text(
            "Sorry, automatic payments are currently unavailable.\n"
            "Please contact the admin for manual activation."
        )
        return

    await context.bot.send_invoice(
        chat_id, title, description, payload,
        PAYMENT_PROVIDER_TOKEN, currency, [LabeledPrice(title, price)]
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answers the pre-checkout query."""
    query = update.pre_checkout_query
    if query.invoice_payload != 'pro-month-payload':
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles a successful payment."""
    # Here you would add the logic to grant pro status to the user in your database
    # db.grant_pro(update.effective_user.id, days=30)
    await update.message.reply_text("✅ Payment successful! You are now a Pro user for 30 days.")