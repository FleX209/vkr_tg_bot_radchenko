import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import TELEGRAM_TOKEN
from handlers import start, handle_image, handle_text, handle_photo_selection
from db_utils import init_db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def main():
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_photo_selection))
    app.run_polling()


if __name__ == '__main__':
    main()

