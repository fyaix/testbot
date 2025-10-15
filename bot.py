import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    PreCheckoutQueryHandler,
)

from config import BOT_TOKEN, states
from database import db_instance as db

# Import handlers from modularized files
from handlers.start import start_command, help_command
from handlers.profile import (
    profile_command, gender_step, age_step, bio_step,
    photo_step, hobby_step, cancel_profile
)
from handlers.matching import (
    find_partner_command, search_pro_command, search_gender_step,
    search_hobby_step, search_age_range_step, proposal_callback,
    next_command, stop_command
)
from handlers.admin import (
    ban_command, unban_command, grant_pro_command,
    broadcast_command, admin_stats_command
)
from handlers.quiz import (
    play_quiz_command, answer_quiz_command, quiz_reward_callback
)
from handlers.feedback import (
    report_command, report_callback, feedback_command, feedback_callback as fb_callback
)
from handlers.payment import (
    upgrade_command, precheckout_callback, successful_payment_callback
)
from handlers.chat import forward_message, secret_mode_command
from utils.decorators import auto_update_profile, check_ban_status

def main() -> None:
    """Sets up and runs the bot."""
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    if not BOT_TOKEN:
        logger.error("FATAL: BOT_TOKEN is not configured. Exiting.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # --- Conversation Handlers ---
    profile_conv = ConversationHandler(
        entry_points=[
            CommandHandler("profile", profile_command),
            MessageHandler(filters.Regex(r"^👤 My Profile$"), profile_command)
        ],
        states={
            states["PROFILE_GENDER"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_step)],
            states["PROFILE_AGE"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_step)],
            states["PROFILE_BIO"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio_step)],
            states["PROFILE_PHOTO"]: [MessageHandler(filters.PHOTO, photo_step)],
            states["PROFILE_HOBBY"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, hobby_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel_profile)],
    )

    search_pro_conv = ConversationHandler(
        entry_points=[
            CommandHandler("searchpro", search_pro_command),
            MessageHandler(filters.Regex(r"^✨ Pro Search$"), search_pro_command)
        ],
        states={
            states["SEARCH_GENDER"]: [CallbackQueryHandler(search_gender_step, pattern=r"^searchgender_")],
            states["SEARCH_HOBBY"]: [CallbackQueryHandler(search_hobby_step, pattern=r"^searchhobby_")],
            states["SEARCH_AGE_MIN"]: [MessageHandler(filters.Regex(r'^\d{1,2}\s*-\s*\d{1,2}$'), search_age_range_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel_profile)], # Can reuse cancel
    )

    # --- Registering Handlers ---
    # Conversation Handlers must be registered before the buttons that trigger them
    application.add_handler(profile_conv)
    application.add_handler(search_pro_conv)

    # Basic commands for direct access
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Button-based commands (using Regex)
    application.add_handler(MessageHandler(filters.Regex(r"^🔍 Find Partner$"), find_partner_command))
    application.add_handler(MessageHandler(filters.Regex(r"^✨ Pro Search$"), search_pro_command))
    application.add_handler(MessageHandler(filters.Regex(r"^👤 My Profile$"), profile_command))
    application.add_handler(MessageHandler(filters.Regex(r"^💎 Upgrade$"), upgrade_command))
    application.add_handler(MessageHandler(filters.Regex(r"^🎮 Play Quiz$"), play_quiz_command))
    # Note: Group join is not implemented yet, so we'll skip that button for now.

    # Text-based commands that are still necessary
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("answer", answer_quiz_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(CommandHandler("secretmode", secret_mode_command))
    
    # Admin commands
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("grantpro", grant_pro_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("adminstats", admin_stats_command))

    # Callback Query Handlers
    application.add_handler(CallbackQueryHandler(profile_command, pattern="^start_profile_setup$"))
    application.add_handler(CallbackQueryHandler(proposal_callback, pattern=r"^proposal_"))
    application.add_handler(CallbackQueryHandler(report_callback, pattern=r"^(report_|block_)"))
    application.add_handler(CallbackQueryHandler(fb_callback, pattern=r"^fb_"))
    application.add_handler(CallbackQueryHandler(quiz_reward_callback, pattern=r"^quiz(pro|poin)_"))

    # Payment Handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # Decorated message handler
    # This applies the decorators to the forward_message handler
    decorated_forward_message = auto_update_profile(check_ban_status(forward_message))

    # General message handler (must be last)
    # We register two separate handlers to avoid mixing legacy and class-based filters
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VOICE,
        decorated_forward_message
    ))
    application.add_handler(MessageHandler(
        filters.Sticker(),
        decorated_forward_message
    ))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()