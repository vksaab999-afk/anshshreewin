import asyncio
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging Setup
logging.basicConfig(level=logging.INFO)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8727719954:AAFLw0h-SOVxsKR_917eivJdWyBCjgHsLYc"

# Admin IDs list
ADMIN_IDS = [5785924075, 8802096404]

# MongoDB Atlas URI
MONGO_URI = "mongodb+srv://anshbhai:shreewin0001@anshshreewin.3ehveho.mongodb.net/?appName=anshshreewin"

# Source Chat & Message IDs (Jahan se messages copy hokar users ko jayenge)
SOURCE_CHAT_ID = 5785924075
MSG_1 = 30  # Pehla message
MSG_2 = 58  # Dusra message
MSG_3 = 32  # Teesra message (Jiske sath Registration button rahega)
# =======================================================

# --- MONGODB SETUP ---
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telegram_bot_db"]
users_collection = db["users"]


def save_user_to_mongo(user_id, first_name, username):
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "first_name": first_name,
                    "username": username,
                }
            },
            upsert=True,
        )
    except Exception as e:
        logging.error(f"MongoDB Error: {e}")


# --- KEEP-ALIVE WEB SERVER ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is Live and MongoDB Connected!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = ThreadingHTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()


# --- INSTANT JOIN REQUEST & WELCOME SEQUENCE ---
async def send_join_sequence(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        await context.bot.copy_message(
            chat_id=user_id, from_chat_id=SOURCE_CHAT_ID, message_id=MSG_1
        )
        await context.bot.copy_message(
            chat_id=user_id, from_chat_id=SOURCE_CHAT_ID, message_id=MSG_2
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "REGISTRATION LINK 🔗",
                    url=(
                        "https://www.shreewin66.com/#/register?invitationCode=31828108076"
                    ),
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=MSG_3,
            reply_markup=reply_markup,
        )

        logging.info(f"Instant welcome sequence sent successfully to {user_id}")
    except Exception as e:
        logging.error(f"Error sending join sequence to {user_id}: {e}")


# --- JOIN REQUEST HANDLER ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user = request.from_user
    save_user_to_mongo(user.id, user.first_name, user.username)
    asyncio.create_task(send_join_sequence(context, user.id))


# --- START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_to_mongo(user.id, user.first_name, user.username)
    await update.message.reply_text(
        "👋 Welcome! Channel join karne par aapko saari details mil jayengi."
    )


# --- BUTTON HANDLER ---
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()


# --- 100% EXACT BROADCAST ENGINE (PRESERVES ANIMATED EMOJIS & MEDIA) ---
async def execute_broadcast(message_to_broadcast, context, admin_chat_id):
    users = list(users_collection.find({}, {"user_id": 1}))
    total_users = len(users)

    if total_users == 0:
        await context.bot.send_message(
            chat_id=admin_chat_id, text="⚠️ Database me koi user nahi hai!"
        )
        return

    progress_msg = await context.bot.send_message(
        chat_id=admin_chat_id,
        text=(
            f"🚀 **Broadcast Started!**\nTotal Users:"
            f" `{total_users}`\nPlease wait..."
        ),
    )

    for u in users:
        u_id = u["user_id"]
        if u_id in ADMIN_IDS:
            continue
        try:
            # Telegram ka native copy_message use kar rahe hain taaki 
            # custom animated emojis, captions, entities aur media exact copy ho.
            await context.bot.copy_message(
                chat_id=u_id,
                from_chat_id=admin_chat_id,
                message_id=message_to_broadcast.message_id,
                reply_markup=message_to_broadcast.reply_markup,
            )
        except Exception as e:
            # Fallback agar copy_message mein koi issue aaye toh direct forward/send try karein
            try:
                await message_to_broadcast.forward(chat_id=u_id)
            except Exception as e2:
                logging.error(f"Broadcast error for {u_id}: {e2}")

    try:
        await context.bot.edit_message_text(
            chat_id=admin_chat_id,
            message_id=progress_msg.message_id,
            text="✅ **Broadcast Completed!**",
            parse_mode="Markdown",
        )
    except:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text="✅ **Broadcast Completed!**",
            parse_mode="Markdown",
        )


# --- AUTO BROADCAST FOR ADMINS ---
async def auto_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if update.effective_user.id not in ADMIN_IDS:
        return
    if msg.text and msg.text.startswith("/"):
        return
    await execute_broadcast(msg, context, update.effective_user.id)


# --- COMMAND BASED BROADCAST ---
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return

    if msg.reply_to_message:
        await execute_broadcast(msg.reply_to_message, context, admin_id)
    else:
        text_after_command = msg.text.replace("/broadcast", "").strip()
        if text_after_command:
            users = list(users_collection.find({}, {"user_id": 1}))
            total_users = len(users)

            progress_msg = await msg.reply_text(
                f"🚀 Broadcast started for {total_users} users..."
            )

            for u in users:
                u_id = u["user_id"]
                if u_id in ADMIN_IDS:
                    continue
                try:
                    await context.bot.send_message(
                        chat_id=u_id, text=text_after_command
                    )
                except:
                    pass

            await progress_msg.edit_text(
                "✅ **Broadcast Completed!**", parse_mode="Markdown"
            )
        else:
            await msg.reply_text(
                "⚠️ Kripya message ke sath /broadcast likhein ya kisi message"
                " par reply karke /broadcast bhejein."
            )


# --- STATS COMMAND ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ADMIN_IDS:
        total_users = users_collection.count_documents({})
        await update.message.reply_text(
            f"📊 **Total Users:** `{total_users}`", parse_mode="Markdown"
        )


def main():
    Thread(target=run_web_server, daemon=True).start()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CallbackQueryHandler(handle_button))

    app.add_handler(
        MessageHandler(filters.User(ADMIN_IDS) & ~filters.COMMAND, auto_broadcast)
    )

    print("Bot is running with native copy_message broadcast engine...")
    app.run_polling(drop_pending_updates=True, close_loop=False)


if __name__ == "__main__":
    main()
