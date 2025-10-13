import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN, WEBHOOK_URL
from database import db

# Import handlers from the new modules
from handlers.start import start_command, help_command
from handlers.matching import (
    search_partner,
    handle_message,
    skip_command,
    stop_command
)
from handlers.admin import admin_panel, admin_stats, admin_reports, report_command
from handlers.premium import (
    premium_info,
    send_invoice,
    precheckout_callback,
    successful_payment_callback
)
from handlers.settings import (
    settings_command,
    set_gender_start, set_gender_save,
    set_gender_pref_start, set_gender_pref_save,
    set_interests_start, set_interests_save,
    cancel_settings,
    GENDER, GENDER_PREFERENCE, INTERESTS
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# BUTTON HANDLER
# ======================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and runs the appropriate handler."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    
    # Route the callback data to the correct function
    if query.data == 'search':
        await search_partner(update, context)
    elif query.data == 'help':
        await help_command(update, context)
    elif query.data == 'premium':
        await premium_info(update, context)
    elif query.data == 'upgrade_premium':
        await send_invoice(update, context)
    elif query.data == 'start_menu':
        await start_command(update, context)
    
    # Admin callbacks
    elif query.data == 'admin_stats':
        await admin_stats(update, context)
    elif query.data == 'admin_reports':
        await admin_reports(update, context)


# ======================
# MAIN FUNCTION
# ======================
def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Register basic command handlers
    from handlers.start import myprofile_command
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("myprofile", myprofile_command))

    # Register matching and chat control handlers
    application.add_handler(CommandHandler("skip", skip_command))
    application.add_handler(CommandHandler("stop", stop_command))

    # Register admin handlers
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("report", report_command))

    # Settings conversation handler
    settings_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_gender_start, pattern='^set_gender$'),
                      CallbackQueryHandler(set_gender_pref_start, pattern='^set_gender_pref$'),
                      CallbackQueryHandler(set_interests_start, pattern='^set_interests$')],
        states={
            GENDER: [CallbackQueryHandler(set_gender_save, pattern='^gender_')],
            GENDER_PREFERENCE: [CallbackQueryHandler(set_gender_pref_save, pattern='^pref_')],
            INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_interests_save)],
        },
        fallbacks=[CallbackQueryHandler(cancel_settings, pattern='^cancel_settings$'),
                   CommandHandler('cancel', cancel_settings)],
        map_to_parent={
            # End of conversation -> back to main button handler
            ConversationHandler.END: ConversationHandler.END,
        }
    )
    
    # Register payment handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    # The main button handler now needs to include the settings conversation
    main_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            ConversationHandler.END: [
                CallbackQueryHandler(button_callback),
                settings_conv_handler
            ]
        },
        fallbacks=[CommandHandler('start', start_command)]
    )

    # The main handler that routes all callbacks and commands.
    # It uses the ConversationHandler for the settings menu.
    application.add_handler(settings_conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Register the main message handler for chatting
    # It handles non-command text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    if WEBHOOK_URL:
        # Production mode (Vercel, etc.)
        # A more robust way to create a unique URL path
        url_path = BOT_TOKEN.split(':', 1)[-1].replace('/', '_')

        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            url_path=url_path,
            webhook_url=f"{WEBHOOK_URL}/{url_path}"
        )
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        # Development mode
        logger.info("Starting bot in polling mode...")
        application.run_polling()

if __name__ == '__main__':
    main()