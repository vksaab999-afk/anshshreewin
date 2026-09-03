import os
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatJoinRequestHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8727719954:AAFLw0h-SOVxsKR_917eivJdWyBCjgHsLYc" 
ADMIN_IDS = [5785924075, 8802096404]
MONGO_URI = "mongodb+srv://anshbhai:shreewin0001@anshshreewin.3ehveho.mongodb.net/?appName=anshshreewin"

SOURCE_CHAT_ID = 5785924075
VIDEO_MSG_ID = 30        # Tutorial Video
APK_MSG_ID = 12          # VIP Hack File (Original caption ke sath)
AUDIO_MSG_ID = 32        # Audio Note

REGISTRATION_LINK = "https://www.shreewin66.com/#/register?invitationCode=31828108076"

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telegram_bot_db"]
users_collection = db["users"]

def save_user_to_mongo(user_id, first_name, username):
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "first_name": first_name, "username": username}},
            upsert=True
        )
    except Exception as e:
        logging.error(f"MongoDB Error: {e}")

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><body><h1>Bot is Live!</h1></body></html>", "utf-8"))
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

async def send_welcome_content(context: ContextTypes.DEFAULT_TYPE, user_id: int, first_name: str):
    try:
        welcome_text = f"𝗪𝗲𝗹𝗰𝗼𝗺𝗲 {first_name} ❤️‍🔥\n\n"
        await context.bot.send_message(chat_id=user_id, text=welcome_text)

        # 1. Tutorial Video
        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=VIDEO_MSG_ID
        )

        # 2. VIP Hack File (Yeh file aur iska original caption dono exact copy kar dega)
        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=APK_MSG_ID
        )

        keyboard = [
            [InlineKeyboardButton("Registration Link 🔗", url=REGISTRATION_LINK)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 3. Audio Note with Button
        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=AUDIO_MSG_ID,
            reply_markup=reply_markup
        )

    except Exception as e:
        logging.error(f"Error: {e}")

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user = request.from_user
    save_user_to_mongo(user.id, user.first_name, user.username)
    await send_welcome_content(context, user.id, user.first_name)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_to_mongo(user.id, user.first_name, user.username)
    await send_welcome_content(context, user.id, user.first_name)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ADMIN_IDS:
        total_users = users_collection.count_documents({})
        await update.message.reply_text(f"📊 **Total Users:** `{total_users}`", parse_mode="Markdown")

def main():
    Thread(target=run_web_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
