import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_ID", "0").split(",")]
CLOSED_CHANNEL_ID = int(os.getenv("CLOSED_CHANNEL_ID", "0"))

# Payment configuration
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "1234 5678 9012 3456")
PAYMENT_RECEIVER = os.getenv("PAYMENT_RECEIVER", "Иван Иванов")

# Subscription prices in rubles
SUBSCRIPTION_PRICES = {
    1: 1000,  # 1 month
    3: 2500,  # 3 months
    12: 8000  # 12 months
} 