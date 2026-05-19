import logging
import asyncio
import psutil
import time
import os
from datetime import datetime
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("8712150869:AAFvVvTygbEMYDZUN9OV9Qu4tloqxsQIvxs")
MONGO_URL = os.getenv("mongodb+srv://s83988364_db_user:CFn6crlU4ecZa3kU@cluster0.xzdx7o4.mongodb.net/?appName=Cluster0")
OWNER_ID = int(os.getenv("8722144519"))
OWNER_USERNAME = os.getenv("@ll_DARK_GETO_ll", "")
GROUP_LINK = os.getenv("https://t.me/+Yu4K5-9LHH1mM2Zl")
SUDO_GROUP_LINK = os.getenv("https://t.me/+zzukV0c4p5swOWRh")

client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
sudo_users_db = db["sudo_users"]
muted_users_db = db["muted_users"]
filters_db = db["filters"]
stickers_db = db["stickers"]
welcome_db = db["welcome"]
owner_settings_db = db["owner_settings"]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

active_spams: Dict[int, asyncio.Task] = {}

async def is_sudo(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return sudo_users_db.find_one({"user_id": user_id}) is not None

async def get_bot_speed() -> dict:
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    ping = round(psutil.net_io_counters().bytes_sent / 1024 / 1024, 2)
    return {"cpu": cpu_percent, "memory": memory_percent, "ping": ping}

async def get_owner_link():
    owner_config = owner_settings_db.find_one({"_id": "owner_config"})
    if owner_config and owner_config.get("username"):
        username = owner_config.get("username").replace('@', '')
        return f"https://t.me/{username}", username
    if OWNER_USERNAME:
        username = OWNER_USERNAME.replace('@', '')
        return f"https://t.me/{username}", username
    return f"tg://user?id={OWNER_ID}", None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_link, owner_uname = await get_owner_link()
    keyboard = [
        [InlineKeyboardButton("➕ Add Me Baby", url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton("🏠 My Home", url=GROUP_LINK),
         InlineKeyboardButton("👑 My Master", url=owner_link)],
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("⚡ Get Sudo", url=SUDO_GROUP_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = "✨ **Bot Started Successfully!** ✨\n\nI'm here to help you manage your groups!"
    if owner_uname:
        caption += f"\n\n👑 **My Master:** @{owner_uname}"
    
    await update.message.reply_text(
        text=caption,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def set_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setowner @username\nExample: /setowner @myusername")
        return
    
    username = context.args[0].replace('@', '')
    
    owner_settings_db.update_one(
        {"_id": "owner_config"},
        {"$set": {"username": username, "updated_at": datetime.now()}},
        upsert=True
    )
    
    await update.message.reply_text(f"✅ Owner username set to: @{username}\n\nNow '👑 My Master' button will open @{username}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **Bot Commands:**

📌 **User Commands:**
• /ping - Check bot speed
• /alive - Check bot status  
• /speed - Bot performance

👑 **Admin Commands:**
• /ban @user - Ban a user
• /mute @user - Mute a user
• /unmute @user - Unmute a user
• /promote @user - Promote to admin
• /filter keyword reply - Save auto-reply
• /welcome message - Set welcome message
• /mention - Mention all members

⚡ **Sudo Commands:**
• .mute - Mute all messages in group
• .unmute - Unmute all messages
• .sticker count - Send multiple stickers
• .spam @user count message - Spam user
• .stopspam - Stop spamming
• .info @user - Get user details

🔧 **Owner Only:**
• .addsudo @user - Add sudo user
• .delsudo @user - Remove sudo user
• .sudolist - List all sudo users
• .mutelist - List all muted users
• .addsticker - Add sticker (reply to sticker)
• /setowner @username - Set owner username

💡 **Tip:** Reply to a user's message to ban/mute/promote them!
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    message = await update.message.reply_text("🏓 Pinging...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000)
    await message.delete()
    speed = await get_bot_speed()
    
    await update.message.reply_text(
        text=f"🏓 **Pong!**\n\n"
             f"⚡ **Response Time:** `{ping_time}ms`\n"
             f"💻 **CPU Usage:** `{speed['cpu']}%`\n"
             f"📊 **Memory Usage:** `{speed['memory']}%`\n"
             f"🌐 **Network:** `{speed['ping']}MB`",
        parse_mode=ParseMode.MARKDOWN
    )

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    speed = await get_bot_speed()
    await update.message.reply_text(
        text=f"✅ **Bot is Alive!**\n\n"
             f"🕒 **Status:** Running 24/7\n"
             f"💻 **CPU:** `{speed['cpu']}%`\n"
             f"📊 **Memory:** `{speed['memory']}%`\n"
             f"🎯 **Ready to work!**",
        parse_mode=ParseMode.MARKDOWN
    )

async def speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ping(update, context)

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    user_id = update.effective_user.id
    member = await update.effective_chat.get_member(user_id)
    
    if not member.can_restrict_members:
        await update.message.reply_text("❌ You don't have permission to ban!")
        return
    
    try:
        if update.message.reply_to_message:
            user_to_ban = update.message.reply_to_message.from_user.id
            name = update.message.reply_to_message.from_user.first_name
        elif context.args:
            username = context.args[0].replace('@', '')
            try:
                user = await context.bot.get_chat(username)
                user_to_ban = user.id
                name = user.first_name
            except:
                await update.message.reply_text("❌ User not found!")
                return
        else:
            await update.message.reply_text("Usage: /ban @username or reply to user")
            return
        
        await update.effective_chat.ban_member(user_to_ban)
        await update.message.reply_text(f"✅ {name} has been banned!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    user_id = update.effective_user.id
    member = await update.effective_chat.get_member(user_id)
    
    if not member.can_restrict_members:
        await update.message.reply_text("❌ You don't have permission to mute!")
        return
    
    if update.message.reply_to_message:
        user_to_mute = update.message.reply_to_message.from_user.id
        name = update.message.reply_to_message.from_user.first_name
        await update.effective_chat.restrict_member(
            user_to_mute,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text(f"✅ {name} has been muted!")
    else:
        await update.message.reply_text("❌ Reply to a user to mute them!")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    if update.message.reply_to_message:
        user_to_unmute = update.message.reply_to_message.from_user.id
        name = update.message.reply_to_message.from_user.first_name
        await update.effective_chat.restrict_member(
            user_to_unmute,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await update.message.reply_text(f"✅ {name} has been unmuted!")
    else:
        await update.message.reply_text("❌ Reply to a user to unmute them!")

async def save_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /filter keyword reply_text\nExample: /filter hi Hello! How are you?")
        return
    
    keyword = context.args[0].lower()
    reply = ' '.join(context.args[1:])
    
    filters_db.update_one(
        {"chat_id": update.effective_chat.id, "keyword": keyword},
        {"$set": {"reply": reply}},
        upsert=True
    )
    await update.message.reply_text(f"✅ Filter saved for '{keyword}'")

async def handle_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.lower()
    filter_data = filters_db.find_one({"chat_id": update.effective_chat.id, "keyword": text})
    
    if filter_data:
        await update.message.reply_text(filter_data['reply'])

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /welcome Your welcome message\nUse {user} for member name")
        return
    
    welcome_msg = ' '.join(context.args)
    welcome_db.update_one(
        {"chat_id": update.effective_chat.id},
        {"$set": {"message": welcome_msg}},
        upsert=True
    )
    await update.message.reply_text("✅ Welcome message saved!")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        welcome_data = welcome_db.find_one({"chat_id": update.effective_chat.id})
        if welcome_data:
            msg = welcome_data['message'].format(user=member.first_name)
            await update.message.reply_text(msg)

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    user_id = update.effective_user.id
    member = await update.effective_chat.get_member(user_id)
    
    if not member.can_promote_members:
        await update.message.reply_text("❌ You don't have permission to promote!")
        return
    
    if update.message.reply_to_message:
        user_to_promote = update.message.reply_to_message.from_user.id
        name = update.message.reply_to_message.from_user.first_name
        await update.effective_chat.promote_member(
            user_to_promote,
            can_change_info=True,
            can_post_messages=True,
            can_edit_messages=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=False
        )
        await update.message.reply_text(f"✅ {name} is now an admin!")
    else:
        await update.message.reply_text("❌ Reply to a user to promote them!")

async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    user_id = update.effective_user.id
    member = await update.effective_chat.get_member(user_id)
    
    if not member.can_mention_all and not await is_sudo(user_id):
        await update.message.reply_text("❌ You need admin rights to mention all!")
        return
    
    admins = []
    async for admin in update.effective_chat.get_administrators():
        if not admin.user.is_bot:
            if admin.user.username:
                admins.append(f"@{admin.user.username}")
            else:
                admins.append(admin.user.first_name)
    
    if admins:
        mentions = " ".join(admins[:15])
        await update.message.reply_text(f"📢 **Admins in this group:**\n{mentions}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("No admins found!")

async def sudo_mute_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_sudo(update.effective_user.id):
        await update.message.reply_text("❌ Only sudo users can use this command!")
        return
    
    if not update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    muted_users_db.update_one(
        {"chat_id": update.effective_chat.id},
        {"$set": {"muted": True, "muted_by": update.effective_user.id}},
        upsert=True
    )
    await update.message.reply_text("🔇 **All users are now muted in this group!**\nOnly admins and sudo users can send messages.", parse_mode=ParseMode.MARKDOWN)

async def sudo_unmute_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_sudo(update.effective_user.id):
        await update.message.reply_text("❌ Only sudo users can use this command!")
        return
    
    if not update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    muted_users_db.delete_many({"chat_id": update.effective_chat.id})
    await update.message.reply_text("🔊 **All users can now send messages in this group!**", parse_mode=ParseMode.MARKDOWN)

async def sudo_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_sudo(update.effective_user.id):
        await update.message.reply_text("❌ Only sudo users can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: .sticker <count>\nExample: .sticker 5")
        return
    
    try:
        count = int(context.args[0])
        if count > 20:
            count = 20
        if count < 1:
            count = 1
        
        stickers = list(stickers_db.find())
        if not stickers:
            await update.message.reply_text("❌ No stickers saved! Use .addsticker to add stickers.")
            return
        
        for i in range(min(count, len(stickers))):
            await update.message.reply_sticker(stickers[i]['sticker_id'])
            await asyncio.sleep(0.5)
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number!")

async def sudo_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_sudo(update.effective_user.id):
        await update.message.reply_text("❌ Only sudo users can use this command!")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text("Usage: .spam @user <count> <message>\nExample: .spam @username 10 Hello!")
        return
    
    user_input = context.args[0].replace('@', '')
    try:
        count = int(context.args[1])
        message = ' '.join(context.args[2:])
        
        if count > 50:
            count = 50
        if count < 1:
            count = 1
        
        try:
            user = await context.bot.get_chat(user_input)
        except:
            await update.message.reply_text("❌ User not found!")
            return
        
        async def spam_task():
            for i in range(count):
                await update.message.reply_text(f"@{user.username if user.username else user_input} {message} [{i+1}]")
                await asyncio.sleep(1)
        
        task = asyncio.create_task(spam_task())
        active_spams[update.effective_chat.id] = task
        await update.message.reply_text(f"✅ Spamming @{user.username if user.username else user_input} for {count} messages!")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid count!")

async def sudo_stopspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_sudo(update.effective_user.id):
        await update.message.reply_text("❌ Only sudo users can use this command!")
        return
    
    if update.effective_chat.id in active_spams:
        active_spams[update.effective_chat.id].cancel()
        del active_spams[update.effective_chat.id]
        await update.message.reply_text("✅ Spamming stopped!")
    else:
        await update.message.reply_text("❌ No active spam in this chat!")

async def sudo_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_sudo(update.effective_user.id):
        await update.message.reply_text("❌ Only sudo users can use this command!")
        return
    
    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        username = context.args[0].replace('@', '')
        try:
            target_user = await context.bot.get_chat(username)
        except:
            await update.message.reply_text("❌ User not found!")
            return
    
    if not target_user:
        await update.message.reply_text("❌ Reply to a user or provide username!")
        return
    
    info_text = f"""
📊 **User Information:**
• **Name:** {target_user.first_name}
• **ID:** `{target_user.id}`
• **Username:** @{target_user.username if target_user.username else 'None'}
• **Is Bot:** {target_user.is_bot}
• **Is Sudo:** {await is_sudo(target_user.id)}
    """
    await update.message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)

async def owner_addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: .addsudo @username\nExample: .addsudo @username")
        return
    
    username = context.args[0].replace('@', '')
    try:
        user = await context.bot.get_chat(username)
        sudo_users_db.update_one(
            {"user_id": user.id},
            {"$set": {"username": username, "added_by": OWNER_ID, "added_at": datetime.now()}},
            upsert=True
        )
        await update.message.reply_text(f"✅ @{username} is now a sudo user!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def owner_delsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: .delsudo @username\nExample: .delsudo @username")
        return
    
    username = context.args[0].replace('@', '')
    result = sudo_users_db.delete_one({"username": username})
    
    if result.deleted_count > 0:
        await update.message.reply_text(f"✅ Removed @{username} from sudo users!")
    else:
        await update.message.reply_text(f"❌ @{username} is not a sudo user!")

async def owner_sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can use this command!")
        return
    
    sudo_users = list(sudo_users_db.find())
    if not sudo_users:
        await update.message.reply_text("No sudo users found!")
        return
    
    text = "👑 **Sudo Users List:**\n\n"
    for i, user in enumerate(sudo_users, 1):
        text += f"{i}. @{user['username']} (ID: `{user['user_id']}`)\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def owner_mutelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can use this command!")
        return
    
    muted_chats = list(muted_users_db.find())
    if not muted_chats:
        await update.message.reply_text("No muted groups found!")
        return
    
    text = "🔇 **Muted Groups List:**\n\n"
    for i, chat in enumerate(muted_chats, 1):
        if chat.get("chat_id"):
            text += f"{i}. Chat ID: `{chat['chat_id']}`\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def owner_addsticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can use this command!")
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.sticker:
        await update.message.reply_text("❌ Reply to a sticker to add it!\nExample: Reply to any sticker with .addsticker")
        return
    
    sticker = update.message.reply_to_message.sticker
    stickers_db.insert_one({
        "sticker_id": sticker.file_id,
        "added_by": OWNER_ID,
        "emoji": sticker.emoji,
        "added_at": datetime.now()
    })
    await update.message.reply_text("✅ Sticker added successfully!")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return
    
    chat_id = update.effective_chat.id
    muted = muted_users_db.find_one({"chat_id": chat_id})
    
    if muted and muted.get("muted", False):
        user_id = update.effective_user.id
        is_user_admin = False
        
        try:
            member = await update.effective_chat.get_member(user_id)
            is_user_admin = member.status in ['administrator', 'creator']
        except:
            pass
        
        if not is_user_admin and not await is_sudo(user_id) and user_id != OWNER_ID:
            try:
                await update.message.delete()
            except:
                pass

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await help_command(update, context)

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("alive", alive))
    application.add_handler(CommandHandler("speed", speed))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("filter", save_filter))
    application.add_handler(CommandHandler("welcome", set_welcome))
    application.add_handler(CommandHandler("promote", promote))
    application.add_handler(CommandHandler("mention", mention_all))
    application.add_handler(CommandHandler("setowner", set_owner))
    
    application.add_handler(MessageHandler(filters.Regex(r'^\.mute$'), sudo_mute_all))
    application.add_handler(MessageHandler(filters.Regex(r'^\.unmute$'), sudo_unmute_all))
    application.add_handler(MessageHandler(filters.Regex(r'^\.sticker\s+\d+$'), sudo_sticker))
    application.add_handler(MessageHandler(filters.Regex(r'^\.spam\s+'), sudo_spam))
    application.add_handler(MessageHandler(filters.Regex(r'^\.stopspam$'), sudo_stopspam))
    application.add_handler(MessageHandler(filters.Regex(r'^\.info\s+'), sudo_info))
    
    application.add_handler(MessageHandler(filters.Regex(r'^\.addsudo\s+'), owner_addsudo))
    application.add_handler(MessageHandler(filters.Regex(r'^\.delsudo\s+'), owner_delsudo))
    application.add_handler(MessageHandler(filters.Regex(r'^\.sudolist$'), owner_sudolist))
    application.add_handler(MessageHandler(filters.Regex(r'^\.mutelist$'), owner_mutelist))
    application.add_handler(MessageHandler(filters.Regex(r'^\.addsticker$'), owner_addsticker))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filter))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.ALL, handle_messages))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 Bot is starting...")
    print(f"✅ Bot username: @{application.bot.username}")
    print(f"👑 Owner ID: {OWNER_ID}")
    if OWNER_USERNAME:
        print(f"👑 Owner Username: @{OWNER_USERNAME}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
