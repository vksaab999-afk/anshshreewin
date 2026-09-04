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

# Logging Setup
logging.basicConfig(level=logging.INFO)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8933004861:AAGx25qg4ckrshSzHlSyNMiFrFLzR4wJSWY" 

# Multiple Admins Support (All 3 Admins)
ADMIN_IDS = [ 5785924075, 8802096404]

# MongoDB Atlas URI
MONGO_URI = "mongodb+srv://anshbhai:shreewin0001@anshshreewin.3ehveho.mongodb.net/?appName=anshshreewin"

# Source Chat & Message IDs
SOURCE_CHAT_ID = 5785924075
VIDEO_MSG_ID = 7        # Tutorial Video
AUDIO_MSG_ID = 325       # Audio Note
APK_MSG_ID =  9         # VIP Hack File

REGISTRATION_LINK = "https://www.shreewin66.com/#/register?invitationCode=31828108076"
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
                    "username": username
                }
            },
            upsert=True
        )
    except Exception as e:
        logging.error(f"MongoDB Error: {e}")

# --- KEEP-ALIVE WEB SERVER (Fixed for UptimeRobot) ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><body><h1>Bot is Live and MongoDB Connected!</h1></body></html>", "utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
    
    def log_message(self, format, *args):
        return  # Yeh line server ke logs ko clean rakhegi taaki faltu print na ho

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# --- WELCOME MESSAGES SENDER FUNCTION ---
async def send_welcome_content(context: ContextTypes.DEFAULT_TYPE, user_id: int, first_name: str):
    try:
        welcome_text = (
            f"👋🏻 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 {first_name} ❤️‍🔥TO OUR PRIVATE SERVER 🔥\n\n"
        )
        await context.bot.send_message(chat_id=user_id, text=welcome_text)

        # Video ke sath do naye custom animated emoji buttons
        video_keyboard = [
            [InlineKeyboardButton("📦 VIP CHANNEL", url="https://t.me/+0IlUS3h89VljNjJl")],
            [InlineKeyboardButton("🔗 REGISTRATION LINK", url="https://www.shreewin66.com/#/register?invitationCode=31828108076")]
        ]
        video_reply_markup = InlineKeyboardMarkup(video_keyboard)

        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=VIDEO_MSG_ID,
            reply_markup=video_reply_markup
        )

        apk_caption = "𝟎 𝐋𝐀𝐕𝐄𝐋  𝐒𝐄𝐑𝐕𝐄𝐑 𝐌𝐎𝐃𝐄 💸"
        primary_admin = ADMIN_IDS[0]
        try:
            msg = await context.bot.forward_message(chat_id=primary_admin, from_chat_id=SOURCE_CHAT_ID, message_id=APK_MSG_ID)
            if msg.document:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=msg.document.file_id,
                    caption=apk_caption
                )
                await context.bot.delete_message(chat_id=primary_admin, message_id=msg.message_id)
            else:
                await context.bot.copy_message(chat_id=user_id, from_chat_id=SOURCE_CHAT_ID, message_id=APK_MSG_ID)
        except Exception:
            await context.bot.copy_message(chat_id=user_id, from_chat_id=SOURCE_CHAT_ID, message_id=APK_MSG_ID)

        # Audio ke sath DM for loss recovery button
        audio_keyboard = [
            [InlineKeyboardButton("💬 DM FOR LOSS RECOVERY", url="https://t.me/m/3Kp2mbceZmMx")]
        ]
        audio_reply_markup = InlineKeyboardMarkup(audio_keyboard)

        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=AUDIO_MSG_ID,
            reply_markup=audio_reply_markup
        )

    except Exception as e:
        logging.error(f"Could not send welcome content to user {user_id}: {e}")

# --- JOIN REQUEST HANDLER ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user = request.from_user
    save_user_to_mongo(user.id, user.first_name, user.username)
    await send_welcome_content(context, user.id, user.first_name)

# --- START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_to_mongo(user.id, user.first_name, user.username)
    await send_welcome_content(context, user.id, user.first_name)

# --- BROADCAST LOGIC ---
async def execute_broadcast(message_to_broadcast, context, admin_chat_id):
    users = list(users_collection.find({"user_id": {"$nin": ADMIN_IDS}}, {"user_id": 1}))
    total_users = len(users)

    if total_users == 0:
        await context.bot.send_message(chat_id=admin_chat_id, text="⚠️ Database me aur koi user nahi hai!")
        return

    for u in users:
        u_id = u["user_id"]
        try:
            if message_to_broadcast.text:
                await context.bot.send_message(chat_id=u_id, text=message_to_broadcast.text, entities=message_to_broadcast.entities)
            elif message_to_broadcast.photo:
                await context.bot.send_photo(chat_id=u_id, photo=message_to_broadcast.photo[-1].file_id, caption=message_to_broadcast.caption, caption_entities=message_to_broadcast.caption_entities)
            elif message_to_broadcast.video:
                await context.bot.send_video(chat_id=u_id, video=message_to_broadcast.video.file_id, caption=message_to_broadcast.caption, caption_entities=message_to_broadcast.caption_entities)
            elif message_to_broadcast.audio:
                await context.bot.send_audio(chat_id=u_id, audio=message_to_broadcast.audio.file_id, caption=message_to_broadcast.caption, caption_entities=message_to_broadcast.caption_entities)
            elif message_to_broadcast.voice:
                await context.bot.send_voice(chat_id=u_id, voice=message_to_broadcast.voice.file_id, caption=message_to_broadcast.caption, caption_entities=message_to_broadcast.caption_entities)
            elif message_to_broadcast.document:
                await context.bot.send_document(chat_id=u_id, document=message_to_broadcast.document.file_id, caption=message_to_broadcast.caption, caption_entities=message_to_broadcast.caption_entities)
            
            await asyncio.sleep(0.04)
        except Exception as e:
            logging.error(f"Error sending to {u_id}: {e}")

    await context.bot.send_message(
        chat_id=admin_chat_id, 
        text="✅ Broadcast Completed!", 
        parse_mode="Markdown"
    )

# --- DIRECT AUTOMATIC BROADCAST ---
async def auto_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if update.effective_user.id not in ADMIN_IDS:
        return
    if msg.text and msg.text.startswith("/"):
        return
    await execute_broadcast(msg, context, update.effective_user.id)

# --- COMMAND BASED BROADCAST ---
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if update.effective_user.id not in ADMIN_IDS:
        return

    if msg.reply_to_message:
        await execute_broadcast(msg.reply_to_message, context, update.effective_user.id)
    else:
        text_after_command = msg.text.replace("/broadcast", "").strip()
        if text_after_command:
            users = list(users_collection.find({"user_id": {"$nin": ADMIN_IDS}}, {"user_id": 1}))
            for u in users:
                try:
                    await context.bot.send_message(chat_id=u["user_id"], text=text_after_command)
                    await asyncio.sleep(0.04)
                except:
                    pass
            await msg.reply_text("✅ Broadcast Completed!")
        else:
            await msg.reply_text("⚠️ Kripya message ke sath /broadcast likhein ya kisi message par reply karke /broadcast bhejein.")

# --- STATS COMMAND ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ADMIN_IDS:
        total_users = users_collection.count_documents({})
        await update.message.reply_text(f"📊 **Total Users:** `{total_users}`", parse_mode="Markdown")

def main():
    Thread(target=run_web_server, daemon=True).start()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    app.add_handler(MessageHandler(filters.User(ADMIN_IDS) & ~filters.COMMAND, auto_broadcast))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
