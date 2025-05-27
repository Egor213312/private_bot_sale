import os
from dotenv import load_dotenv

load_dotenv()
 
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID закрытого канала 