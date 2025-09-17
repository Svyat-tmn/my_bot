import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [123456789]  # Замените на ваш Telegram ID
DB_NAME = "bot_database.db"
