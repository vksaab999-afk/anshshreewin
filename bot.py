import asyncio
import logging
import os
from flask import Flask
from pymongo import MongoClient
from telegram import ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import threading

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Configurations
TOKEN = "8727719954:AAFLw0h-SOVxsKR_917eivJdWyBCjgHsLYc"
MONGO_URI = "mongodb+srv://anshbhai:shreewin0001@anshshreewin.3ehveho.mongodb.net/?appName=anshshreewin"
ADMINS = [5785924075, 8802096404]

# Exact Message IDs (Bot chat se nikali hui)
MSG_1_ID = 30  # Pehla message
MSG_2_ID = 58  # Dusra message
MSG_3_ID = 32  # Teesra message (Jiske sath button rahega)

# MongoDB Connection
client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]
users_collection = db["users"]

# Flask App for Render Keep-Alive (24x7 Active)
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is active and running smoothly!"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)


# 1. Join Request Handler (Instant Messages via ID & Save User)
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req: ChatJoinRequest = update.chat_join_request
    user = req.from_user
    user_id = user.id
    username = user.username or "N/A"
    first_name = user.first_name or "User"

    # Save user to MongoDB (if not already exists)
    try:
        if not users_collection.find_one({"user_id": user_id}):
            users_collection.insert_one(
                {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                }
            )
            logger.info(f"New user saved: {user_id} ({first_name})")
    except Exception as e:
        logger.error(f"Database error while saving user: {e}")

    # Automatically approve the join request
    try:
        await req.approve()
    except Exception as e:
        logger.error(f"Failed to approve join request: {e}")

    # Registration Link Button for 3rd Message
    keyboard = [
        [
            InlineKeyboardButton(
                "🔗 Registration Link",
                url="https://www.shreewin66.com/#/register?invitationCode=31828108076",
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # 1st Message bhejo (ID: 30)
        await context.bot.copy_message(
            chat_id=user_id, from_chat_id=user_id, message_id=MSG_1_ID
        )
        # 2nd Message bhejo (ID: 58)
        await context.bot.copy_message(
            chat_id=user_id, from_chat_id=user_id, message_id=MSG_2_ID
        )
        # 3rd Message button ke sath bhejo (ID: 32)
        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=user_id,
            message_id=MSG_3_ID,
            reply_markup=reply_markup,
        )

        logger.info(
            f"All 3 premium welcome messages successfully sent to user {user_id}"
        )
    except Exception as e:
        logger.error(
            f"Failed to send messages via ID to {user_id} (Check if bot can access messages): {e}"
        )


# 2. Stats Command (/stats - Admin Only)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Aap is command ke liye authorized nahi hain.")
        return

    total_users = users_collection.count_documents({})
    await update.message.reply_text(
        f"📊 **Bot Statistics:**\n\n👥 Total Saved Users: `{total_users}`",
        parse_mode="Markdown",
    )


# 3. Admin Broadcast Handler (Jab admin kuch bheje toh sabhi ko jaye)
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        return

    message = update.message
    if not message:
        return

    all_users = list(users_collection.find({}, {"user_id": 1}))
    if not all_users:
        await message.reply_text("⚠️ Database mein koi user nahi mila broadcast ke liye.")
        return

    success_count = 0
    fail_count = 0

    status_msg = await message.reply_text(
        f"📢 Broadcast shuru ho raha hai total {len(all_users)} users ko..."
    )

    for u in all_users:
        uid = u["user_id"]
        try:
            await message.copy(chat_id=uid)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {uid}: {e}")
            fail_count += 1

    await status_msg.edit_text(
        f"✅ **Broadcast Completed!**\n\n"
        f"✔️ Success: {success_count}\n"
        f"❌ Failed: {fail_count}"
    )


def main():
    # Start Flask server in background thread for Render Uptime (Keep-Alive)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Event loop fix for Python 3.10+ / Render environment
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    application = ApplicationBuilder().token(TOKEN).build()

    # Register Handlers
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast)
    )
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.VIDEO | filters.Document.ALL, admin_broadcast
        )
    )

    logger.info("Bot is starting polling with ID forwarding...")
    application.run_polling()


if __name__ == "__main__":
    main()
