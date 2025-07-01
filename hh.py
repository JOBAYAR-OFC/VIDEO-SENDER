import telebot
import requests
import time
import json
import os
import random
import string
import logging
import re
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===================== CONFIGURATION =====================
class Config:
    # Bot Credentials
    BOT_TOKEN = "7405644678:AAEE-7RgD2bf4gRlmKnBoDw7_znhDCtLsJQ"
    OWNER_ID = 6585974275
    
    # Channels & Groups
    CHANNELS = ["@GHOST_XMOD", "@GST_X_STATUS", "@GHOST_XBACKUP", "@GHOST_CHEATERS"]
    GROUP_LINK = "https://t.me/GHOST_XTOOLS"
    CHANNEL_JOIN_LINK = "https://t.me/addlist/MFPtUKvjAs8xYTk1"  # New channel join link
    
    # API Endpoints
    LIKE_API_URL = "https://ghost-mod-x-pro.vercel.app/like"
    VISIT_API_URL = "https://ghost-x-visit-api.vercel.app"
    PROFILE_API_URL = "https://aditya-info-v11op.onrender.com/player-info"
    BANNER_API_URL = "https://aditya-banner-v11op.onrender.com/banner-image"
    OUTFIT_API_URL = "https://aditya-outfit-v11op.onrender.com/outfit-image"
    LEADERBOARD_API_URL = "https://ariflexlabs-leaderboard-api.vercel.app"
    
    # Media URLs
    VIDEO_URL = "https://github.com/JOBAYAR-OFC/VIDEO-SENDER/blob/main/lv_0_20250620120147.mp4?raw=true"
    SUCCESS_VIDEO = "https://github.com/JOBAYAR-OFC/VIDEO-SENDER/blob/main/jujutsu%20kaisen(MP4).mp4?raw=true"
    
    # Other Settings
    SHORTENER_API = "788912cfe95baf10b57126285ce5166bb3ba85e3"
    SHORTENER_URL = "https://earnlinks.in/api"
    VISIT_COOLDOWN = 120
    VERIFICATION_COOLDOWN = 1200  # 20 minutes
    FREE_USER_DAILY_LIMIT = 1
    VIP_USER_DAILY_LIMIT = 5
    RESET_TIME = 7  # 7 AM reset time
    VERIFICATION_VIDEO_ENABLED = True  # New: Control whether to send verification video
# ========================================================

# Initialize bot
bot = telebot.TeleBot(Config.BOT_TOKEN, parse_mode='HTML')

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self):
        self.vip_users = set()
        self.verification_credits = {}
        self.used_tokens = set()
        self.user_last_verification = {}
        self.pending_requests = {}
        self.token_to_user = {}
        self.vip_expiry = {}
        self.visit_cooldowns = {}
        self.user_coins = {}
        self.all_users = set()
        self.bot_active = True
        self.user_daily_likes = {}  # {user_id: {'count': X, 'date': 'YYYY-MM-DD'}}
        self.custom_limits = {}  # {user_id: limit}
        self.verification_enabled = True  # New: Verification system on/off
        self.load_data()

    def save_data(self):
        data = {
            'vip_users': list(self.vip_users),
            'verification_credits': self.verification_credits,
            'used_tokens': list(self.used_tokens),
            'user_last_verification': self.user_last_verification,
            'pending_requests': {k: {'region': v['region'], 'uid': v['uid'], 'type': v['type']} 
                               for k, v in self.pending_requests.items()},
            'token_to_user': self.token_to_user,
            'vip_expiry': self.vip_expiry,
            'visit_cooldowns': self.visit_cooldowns,
            'user_coins': self.user_coins,
            'all_users': list(self.all_users),
            'bot_active': self.bot_active,
            'user_daily_likes': self.user_daily_likes,
            'custom_limits': self.custom_limits,
            'verification_enabled': self.verification_enabled  # New: Save verification state
        }
        with open('bot_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    def load_data(self):
        if os.path.exists('bot_data.json'):
            with open('bot_data.json', 'r') as f:
                data = json.load(f)
                self.vip_users = set(data.get('vip_users', []))
                self.verification_credits = data.get('verification_credits', {})
                self.used_tokens = set(data.get('used_tokens', []))
                self.user_last_verification = data.get('user_last_verification', {})
                self.token_to_user = data.get('token_to_user', {})
                self.vip_expiry = data.get('vip_expiry', {})
                self.visit_cooldowns = data.get('visit_cooldowns', {})
                self.user_coins = data.get('user_coins', {})
                self.all_users = set(data.get('all_users', []))
                self.bot_active = data.get('bot_active', True)
                self.user_daily_likes = data.get('user_daily_likes', {})
                self.custom_limits = data.get('custom_limits', {})
                self.verification_enabled = data.get('verification_enabled', True)  # New: Load verification state
                
                self.pending_requests = {}
                for user_id, req_data in data.get('pending_requests', {}).items():
                    self.pending_requests[int(user_id)] = {
                        'message': None,
                        'region': req_data['region'],
                        'uid': req_data['uid'],
                        'type': req_data['type']
                    }

    def reset_daily_counts(self):
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        
        # Check if it's time to reset (after 7 AM)
        if now.hour >= Config.RESET_TIME:
            reset_date = now.strftime('%Y-%m-%d')
        else:
            reset_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        
        for user_id in list(self.user_daily_likes.keys()):
            user_data = self.user_daily_likes[user_id]
            if user_data['date'] != reset_date:
                # Reset the count and update the date
                self.user_daily_likes[user_id] = {'count': 0, 'date': today}
        
        self.save_data()

    def can_send_like(self, user_id):
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        
        # Get user's limit
        if user_id in self.custom_limits:
            daily_limit = self.custom_limits[user_id]
        elif is_vip(user_id):
            daily_limit = Config.VIP_USER_DAILY_LIMIT
        else:
            daily_limit = Config.FREE_USER_DAILY_LIMIT
        
        # Initialize or update user's daily count
        if user_id not in self.user_daily_likes or self.user_daily_likes[user_id]['date'] != today:
            self.user_daily_likes[user_id] = {'count': 0, 'date': today}
            self.save_data()
        
        # Check if user can send like
        if self.user_daily_likes[user_id]['count'] < daily_limit:
            return True, daily_limit - self.user_daily_likes[user_id]['count']
        
        return False, 0

    def increment_like_count(self, user_id):
        today = datetime.now().strftime('%Y-%m-%d')
        if user_id not in self.user_daily_likes or self.user_daily_likes[user_id]['date'] != today:
            self.user_daily_likes[user_id] = {'count': 1, 'date': today}
        else:
            self.user_daily_likes[user_id]['count'] += 1
        self.save_data()

    def decrement_like_count(self, user_id):
        today = datetime.now().strftime('%Y-%m-%d')
        if user_id in self.user_daily_likes and self.user_daily_likes[user_id]['date'] == today:
            if self.user_daily_likes[user_id]['count'] > 0:
                self.user_daily_likes[user_id]['count'] -= 1
                self.save_data()

db = DataStorage()

# ===================== UTILITY FUNCTIONS =====================
def shorten_url(url):
    try:
        params = {
            'api': Config.SHORTENER_API,
            'url': url,
            'format': 'text'
        }
        response = requests.get(Config.SHORTENER_URL, params=params, timeout=10)
        
        if response.status_code == 200 and response.text.startswith(('http://', 'https://')):
            return response.text.strip()
        else:
            logger.error(f"Shortener API returned invalid response: {response.text}")
            return url
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
        return url

def is_subscribed(user_id):
    not_joined = []
    for channel in Config.CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    return not_joined

def call_like_api(region, uid):
    try:
        response = requests.get(f"{Config.LIKE_API_URL}?server_name={region}&uid={uid}", timeout=15)
        return response.json() if response.status_code == 200 else {"status": 0, "error": "API_ERROR"}
    except Exception as e:
        logger.error(f"Like API Error: {e}")
        return {"status": 0, "error": "CONNECTION_ERROR"}

def call_visit_api(region, uid):
    try:
        response = requests.get(f"{Config.VISIT_API_URL}/{region}/{uid}", timeout=15)
        return response.json() if response.status_code == 200 else {"error": "API_ERROR"}
    except Exception as e:
        logger.error(f"Visit API Error: {e}")
        return {"error": "CONNECTION_ERROR"}

def call_leaderboard_api(mode, region=None):
    try:
        url = f"{Config.LEADERBOARD_API_URL}/{mode}/leaderboard?key=arii"
        if region:
            url += f"&region={region}"
        response = requests.get(url, timeout=15)
        return response.json() if response.status_code == 200 else {"error": "API_ERROR"}
    except Exception as e:
        logger.error(f"Leaderboard API Error: {e}")
        return {"error": "CONNECTION_ERROR"}

def generate_verification_token(user_id):
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    db.token_to_user[token] = user_id
    db.save_data()
    return token

def is_vip(user_id):
    if user_id in db.vip_users or user_id == Config.OWNER_ID:
        if user_id in db.vip_expiry:
            if time.time() < db.vip_expiry[user_id]:
                return True
            else:
                db.vip_users.remove(user_id)
                del db.vip_expiry[user_id]
                db.save_data()
                return False
        return True
    return False

def get_profile_info(uid, region):
    url = f"{Config.PROFILE_API_URL}?uid={uid}&region={region}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error(f"Error fetching profile info: {e}")
        return None

def format_timestamp(ts):
    try:
        if isinstance(ts, str) and ts.isdigit():
            ts = int(ts)
        return datetime.fromtimestamp(ts).strftime('%d %B %Y %H:%M:%S')
    except:
        return "Not Available"

def get_user_info(user_id):
    try:
        user = bot.get_chat(user_id)
        username = f"@{user.username}" if user.username else f"ID: {user_id}"
        name = user.first_name or ""
        if user.last_name:
            name += f" {user.last_name}"
        return username, name.strip()
    except:
        return f"ID: {user_id}", f"User {user_id}"

def is_admin(user_id):
    return user_id == Config.OWNER_ID

def check_bot_active(message):
    if not db.bot_active:
        bot.reply_to(message, "🔴 <b>BOT IS CURRENTLY OFFLINE</b>\n\nPlease wait until the bot is back online.")
        return False
    return True

def create_verification_message(user_id, region, uid, command_type):
    token = generate_verification_token(user_id)
    verify_url = f"https://t.me/{bot.get_me().username}?start=verify_{token}"
    short_url = shorten_url(verify_url)
    
    db.pending_requests[user_id] = {
        'message': None,
        'region': region,
        'uid': uid,
        'type': command_type
    }
    db.save_data()
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("♻️ 𝗖𝗟𝗜𝗖𝗞 𝗧𝗢 𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡 ♻️", url=short_url))
    kb.add(InlineKeyboardButton("⁉️ 𝗛𝗢𝗪 𝗧𝗢 𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡 ⁉️", url="https://t.me/GST_X_STATUS/100"))
    kb.add(InlineKeyboardButton("💱 𝗕𝗨𝗬 𝗣𝗥𝗘𝗠𝗨𝗔𝗠 💱", url="https://t.me/GHOST_HELPLINE_BOT"))
    
    if Config.VERIFICATION_VIDEO_ENABLED:
        return {
            'video': Config.VIDEO_URL,
            'caption': (
                "🔐 <b>GHOST X VERIFICATION SYSTEM</b> 🔐\n\n"
                f"🆔 <b>UID:</b> <code>{uid}</code>\n"
                f"🌍 <b>Region:</b> {region.upper()}\n"
                f"💎 <b>Type:</b> {'LIKE' if command_type == 'like' else 'VISIT'}\n\n"
                "📌 <b>VERIFICATION STEPS:</b>\n"
                "1️⃣ Click <b>FAST VERIFY NOW</b> button\n"
                "2️⃣ Complete the verification process\n"
                "3️⃣ Return to group to use your credit\n\n"
                "⚠️ <i>Each verification link can only be used once</i>\n"
                "⏳ <i>Verification expires in 20 minutes</i>\n\n"
                "💡 <b>TIP:</b> Get VIP to skip verification!"
            ),
            'reply_markup': kb
        }
    else:
        return {
            'text': (
                "🔐 <b>GHOST X VERIFICATION SYSTEM</b> 🔐\n\n"
                f"🆔 <b>UID:</b> <code>{uid}</code>\n"
                f"🌍 <b>Region:</b> {region.upper()}\n"
                f"💎 <b>Type:</b> {'LIKE' if command_type == 'like' else 'VISIT'}\n\n"
                "📌 <b>VERIFICATION STEPS:</b>\n"
                "1️⃣ Click <b>FAST VERIFY NOW</b> button\n"
                "2️⃣ Complete the verification process\n"
                "3️⃣ Return to group to use your credit\n\n"
                "🔗 <b>Verification Link:</b>\n"
                f"<code>{short_url}</code>\n\n"
                "⚠️ <i>Each verification link can only be used once</i>\n"
                "⏳ <i>Verification expires in 20 minutes</i>\n\n"
                "💡 <b>TIP:</b> Get VIP to skip verification!"
            ),
            'reply_markup': kb
        }

def format_leaderboard(data, mode):
    if not data or not data.get('success'):
        return "❌ Failed to fetch leaderboard data. Please try again later."
    
    leaderboard_info = data.get(f"{mode}_rank_leaderboard_info", []) if mode != "bp" else data.get("booyah_pass_leaderboard_info", [])
    
    if not leaderboard_info:
        return "❌ No leaderboard data available for this mode."
    
    leaderboard_text = f"🏆 <b>{mode.upper()} LEADERBOARD</b> 🏆\n\n"
    
    for i, player in enumerate(leaderboard_info[:50], 1):
        name = player.get('name', 'Unknown')
        score = player.get('br_rank_score', 0) if mode == "br" else player.get('cs_rank_score', 0) if mode == "cs" else player.get('booyah_pass_count', 0)
        level = player.get('level', 'N/A')
        likes = player.get('likes', 'N/A')
        region = player.get('region', 'N/A')
        
        leaderboard_text += (
            f"<b>{i}.</b> {name}\n"
            f"╰┈➤ <b>Score:</b> {score} | <b>Level:</b> {level}\n"
            f"╰┈➤ <b>Likes:</b> {likes} | <b>Region:</b> {region}\n\n"
        )
    
    return leaderboard_text

def get_next_reset_time():
    now = datetime.now()
    if now.hour >= Config.RESET_TIME:
        # Move to next day, handling month/year boundaries
        try:
            reset_time = now + timedelta(days=1)
            reset_time = datetime(reset_time.year, reset_time.month, reset_time.day, Config.RESET_TIME, 0, 0)
        except ValueError:
            # Handle end of month case
            if now.month == 12:
                reset_time = datetime(now.year + 1, 1, 1, Config.RESET_TIME, 0, 0)
            else:
                reset_time = datetime(now.year, now.month + 1, 1, Config.RESET_TIME, 0, 0)
    else:
        reset_time = datetime(now.year, now.month, now.day, Config.RESET_TIME, 0, 0)
    return reset_time.strftime('%d %B %Y at %H:%M:%S')

# ===================== ADMIN COMMANDS =====================
@bot.message_handler(commands=['verification-on'])
def enable_verification(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not authorized to use this command!")
        return
    
    db.verification_enabled = True
    db.save_data()
    bot.reply_to(message, "✅ <b>Verification system has been enabled</b>\n\nAll users will now need to verify before using commands.")

@bot.message_handler(commands=['verification-off'])
def disable_verification(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not authorized to use this command!")
        return
    
    db.verification_enabled = False
    db.save_data()
    bot.reply_to(message, "❌ <b>Verification system has been disabled</b>\n\nUsers can now use commands without verification.")

@bot.message_handler(commands=['verification_video_on'])
def enable_verification_video(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not authorized to use this command!")
        return
    
    Config.VERIFICATION_VIDEO_ENABLED = True
    bot.reply_to(message, "✅ <b>Verification video has been enabled</b>\n\nVerification messages will now include video.")

@bot.message_handler(commands=['verification_video_off'])
def disable_verification_video(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not authorized to use this command!")
        return
    
    Config.VERIFICATION_VIDEO_ENABLED = False
    bot.reply_to(message, "❌ <b>Verification video has been disabled</b>\n\nVerification messages will now be text only.")

@bot.message_handler(commands=['ghost-off'])
def ghost_off(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not authorized to use this command!")
        return
    
    db.bot_active = False
    db.save_data()
    bot.reply_to(message, "🔴 <b>BOT HAS BEEN TURNED OFF</b>\n\nNo commands will work until the bot is turned back on.")

@bot.message_handler(commands=['ghost-on'])
def ghost_on(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not authorized to use this command!")
        return
    
    db.bot_active = True
    db.save_data()
    bot.reply_to(message, "🟢 <b>BOT HAS BEEN TURNED ON</b>\n\nAll commands are now working normally.")

@bot.message_handler(commands=['addvip'])
def add_vip(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        
        if len(args) < 3:
            bot.reply_to(message,
                "✨ <b>VIP ADDITION COMMAND</b> ✨\n\n"
                "<code>/addvip &lt;duration&gt; &lt;user_id/@username&gt;</code>\n\n"
                "⏳ <b>Duration Examples:</b>\n"
                "<code>30min</code>, <code>2hours</code>, <code>15days</code>, <code>perm</code>\n\n"
                "💎 <b>Examples:</b>\n"
                "<code>/addvip 30min @username</code>\n"
                "<code>/addvip 2hours 123456789</code>\n"
                "<code>/addvip perm @user</code>",
                parse_mode='HTML'
            )
            return
        
        duration_input = args[1].lower()
        target_input = args[2]
        
        try:
            if target_input.startswith('@'):
                user_info = bot.get_chat(target_input)
                target = user_info.id
            else:
                target = int(target_input)
        except:
            bot.reply_to(message, "❌ Invalid user specified")
            return
        
        if target in db.vip_users:
            bot.reply_to(message, "⚠️ User is already VIP")
            return
        
        if duration_input == 'perm':
            expiry = 'Permanent'
            db.vip_users.add(target)
            expiry_time = None
        else:
            match = re.match(r'^(\d+)(min|mins|minute|minutes|hour|hours|day|days)$', duration_input)
            if not match:
                bot.reply_to(message, "❌ Invalid duration format. Examples: 30min, 2hours, 15days")
                return
            
            amount = int(match.group(1))
            unit = match.group(2).lower()
            
            if unit.startswith('min'):
                expiry_time = time.time() + (amount * 60)
                expiry = f"{amount} minute(s)"
            elif unit.startswith('hour'):
                expiry_time = time.time() + (amount * 3600)
                expiry = f"{amount} hour(s)"
            elif unit.startswith('day'):
                expiry_time = time.time() + (amount * 86400)
                expiry = f"{amount} day(s)"
            
            db.vip_users.add(target)
            db.vip_expiry[target] = expiry_time
        
        db.save_data()
        
        try:
            user = bot.get_chat(target)
            username = f"@{user.username}" if user.username else str(target)
        except:
            username = str(target)
        
        bot.reply_to(message,
            f"🎉 <b>VIP STATUS GRANTED</b> 🎉\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"🆔 <b>ID:</b> <code>{target}</code>\n"
            f"⏳ <b>Duration:</b> {expiry}\n"
            f"🔑 <b>Added by:</b> @{message.from_user.username}",
            parse_mode='HTML'
        )
        
        try:
            bot.send_message(
                target,
                f"✨ <b>🌟 VIP MEMBERSHIP ACTIVATED 🌟</b> ✨\n\n"
                f"⏳ <b>Duration:</b> {expiry}\n"
                f"📅 <b>Activated at:</b> {datetime.now().strftime('%d %B %Y %H:%M:%S')}\n\n"
                f"Thank you for being part of our VIP community!",
                parse_mode='HTML'
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"Add VIP error: {e}")
        bot.reply_to(message, "⚠️ Error processing command")

@bot.message_handler(commands=['dvip'])
def remove_vip(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    try:
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
        else:
            target = int(message.text.split()[1])

        if target in db.vip_users:
            db.vip_users.remove(target)
            if target in db.vip_expiry:
                del db.vip_expiry[target]
            db.save_data()
            bot.reply_to(message, f"🚫 REMOVED {target} FROM VIP LIST")
        else:
            bot.reply_to(message, "⚠️ This user is not in VIP list")
    except:
        bot.reply_to(message, "⚠️ Usage: Reply to user or provide user ID")

@bot.message_handler(commands=['vips'])
def list_vips(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    if not db.vip_users:
        bot.reply_to(message, "No VIP users yet.")
        return
    
    text = "👑 VIP Users:\n"
    for user_id in db.vip_users:
        expiry = db.vip_expiry.get(user_id, "Permanent")
        if expiry != "Permanent":
            expiry = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry))
        try:
            user = bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else str(user_id)
        except:
            username = str(user_id)
        text += f"{username} - Expires: {expiry}\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['addc'])
def add_coins(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, 
                "💎 <b>Add Coins Command</b> 💎\n\n"
                "<code>/addc &lt;amount&gt; &lt;user_id/@username&gt;</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/addc 100 123456789</code>\n"
                "<code>/addc 50 @username</code>",
                parse_mode='HTML')
            return
        
        amount = int(args[1])
        target_input = args[2]
        
        try:
            if target_input.startswith('@'):
                user_info = bot.get_chat(target_input)
                target = user_info.id
            else:
                target = int(target_input)
        except:
            bot.reply_to(message, "❌ Invalid user specified")
            return
        
        db.user_coins[target] = db.user_coins.get(target, 0) + amount
        db.all_users.add(target)
        db.save_data()
        
        username, name = get_user_info(target)
        
        bot.reply_to(message,
            f"💰 <b>COINS ADDED SUCCESSFULLY!</b>\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"📛 <b>Name:</b> {name}\n"
            f"🆔 <b>ID:</b> {target}\n"
            f"🪙 <b>Added:</b> {amount} coins\n"
            f"💎 <b>New Balance:</b> {db.user_coins.get(target, 0)} coins",
            parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Error in add_coins: {e}")
        bot.reply_to(message, "❌ Error processing command")

@bot.message_handler(commands=['dcn'])
def deduct_coins(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, 
                "💎 <b>Deduct Coins Command</b> 💎\n\n"
                "<code>/dcn &lt;amount/all&gt; &lt;user_id/@username&gt;</code>\n\n"
                "<b>Examples:</b>\n"
                "<code>/dcn 50 123456789</code>\n"
                "<code>/dcn all @username</code>",
                parse_mode='HTML')
            return
        
        amount_input = args[1].lower()
        target_input = args[2]
        
        try:
            if target_input.startswith('@'):
                user_info = bot.get_chat(target_input)
                target = user_info.id
            else:
                target = int(target_input)
        except:
            bot.reply_to(message, "❌ Invalid user specified")
            return
        
        if amount_input == 'all':
            amount = db.user_coins.get(target, 0)
        else:
            amount = int(amount_input)
            
        current = db.user_coins.get(target, 0)
        
        if current < amount:
            bot.reply_to(message, f"❌ User only has {current} coins")
            return
            
        db.user_coins[target] = current - amount
        db.save_data()
        
        username, name = get_user_info(target)
        
        bot.reply_to(message,
            f"💰 <b>COINS DEDUCTED SUCCESSFULLY!</b>\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"📛 <b>Name:</b> {name}\n"
            f"🆔 <b>ID:</b> {target}\n"
            f"🪙 <b>Deducted:</b> {amount} coins\n"
            f"💎 <b>New Balance:</b> {db.user_coins.get(target, 0)} coins",
            parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Error in deduct_coins: {e}")
        bot.reply_to(message, "❌ Error processing command")

@bot.message_handler(commands=['coins'])
def check_coins(message):
    if not check_bot_active(message):
        return
    
    try:
        args = message.text.split()
        target = message.from_user.id
        
        if len(args) > 1 and is_admin(message.from_user.id):
            target_input = args[1]
            try:
                if target_input.startswith('@'):
                    user_info = bot.get_chat(target_input)
                    target = user_info.id
                else:
                    target = int(target_input)
            except:
                bot.reply_to(message, "❌ Invalid user specified")
                return
        
        coins = db.user_coins.get(target, 0)
        username, name = get_user_info(target)
        
        # Get daily like info
        can_send, remaining = db.can_send_like(target)
        if target in db.custom_limits:
            limit_type = "Custom"
            daily_limit = db.custom_limits[target]
        elif is_vip(target):
            limit_type = "VIP"
            daily_limit = Config.VIP_USER_DAILY_LIMIT
        else:
            limit_type = "Free"
            daily_limit = Config.FREE_USER_DAILY_LIMIT
        
        response = (
            f"✨ <b>GHOST X COIN BALANCE</b> ✨\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"📛 <b>Name:</b> {name}\n"
            f"🆔 <b>ID:</b> <code>{target}</code>\n\n"
            f"💰 <b>Coin Balance:</b>\n"
            f"╰┈➤ <b>{coins} Coins</b>\n\n"
            f"🌟 <b>Status:</b> {limit_type} User\n"
            f"💎 <b>Daily Like Limit:</b> {daily_limit}\n"
            f"🔥 <b>Likes Remaining Today:</b> {remaining}\n"
            f"📅 <b>Next Reset:</b> {get_next_reset_time()}"
        )
        
        bot.reply_to(message, response, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in check_coins: {e}")
        bot.reply_to(message, "❌ Error checking coin balance")

@bot.message_handler(commands=['broadcast', 'modhu'])
def broadcast_message(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Please reply to a message to broadcast it")
        return
    
    # For /modhu command, add special formatting
    is_modhu = message.text.startswith('/modhu')
    
    if is_modhu:
        confirm_text = (
            "📢 <b>OFFICIAL BROADCAST MESSAGE</b> 📢\n\n"
            "🔰 <b>From: GHOST X ADMIN TEAM</b>\n\n"
            "This is an official broadcast message from GHOST X.\n"
            f"It will be sent to {len(db.all_users)} users.\n\n"
            "Are you sure you want to proceed?"
        )
    else:
        confirm_text = (
            "⚠️ <b>BROADCAST CONFIRMATION</b>\n\n"
            f"This message will be sent to {len(db.all_users)} users\n\n"
            "Are you sure you want to proceed?"
        )
    
    confirm_kb = InlineKeyboardMarkup()
    confirm_kb.add(
        InlineKeyboardButton("✅ Confirm Broadcast", callback_data="broadcast_confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
    )
    
    bot.reply_to(message,
        confirm_text,
        reply_markup=confirm_kb,
        reply_to_message_id=message.reply_to_message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('broadcast_'))
def handle_broadcast_confirmation(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ You are not authorized!", show_alert=True)
        return
    
    if call.data == "broadcast_cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "Broadcast cancelled")
        return
    
    bot.answer_callback_query(call.id, "Starting broadcast...")
    
    original_message = call.message.reply_to_message
    total_users = len(db.all_users)
    success_users = 0
    failed_users = 0
    
    status_msg = bot.edit_message_text(
        "📢 <b>BROADCAST IN PROGRESS</b>\n\n"
        f"• Users: 0/{total_users}",
        call.message.chat.id,
        call.message.message_id
    )
    
    for user_id in db.all_users:
        try:
            # For /modhu broadcasts, add a header
            if call.message.reply_to_message.text.startswith('/modhu'):
                header = (
                    "📢 <b>OFFICIAL BROADCAST MESSAGE</b> 📢\n\n"
                    "🔰 <b>From: GHOST X ADMIN TEAM</b>\n\n"
                )
                bot.send_message(
                    user_id,
                    header,
                    parse_mode='HTML'
                )
            
            bot.copy_message(
                user_id,
                original_message.chat.id,
                original_message.message_id
            )
            success_users += 1
        except Exception as e:
            failed_users += 1
            logger.error(f"Failed to send to user {user_id}: {e}")
        
        if success_users % 10 == 0 or user_id == list(db.all_users)[-1]:
            bot.edit_message_text(
                "📢 <b>BROADCAST IN PROGRESS</b>\n\n"
                f"• Users: {success_users}/{total_users}",
                call.message.chat.id,
                status_msg.message_id
            )
    
    bot.edit_message_text(
        "✅ <b>BROADCAST COMPLETED</b>\n\n"
        f"👤 <b>Users:</b> {success_users} success, {failed_users} failed\n\n"
        f"📅 <b>Completed at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        call.message.chat.id,
        status_msg.message_id
    )

@bot.message_handler(commands=['addremind'])
def add_custom_limit(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message,
                "💎 <b>Add Custom Limit Command</b> 💎\n\n"
                "<code>/addremind &lt;limit&gt; &lt;user_id/@username&gt;</code>\n\n"
                "<b>Examples:</b>\n"
                "<code>/addremind 5 123456789</code>\n"
                "<code>/addremind 10 @username</code>",
                parse_mode='HTML'
            )
            return
        
        try:
            limit = int(args[1])
            if limit < 1:
                raise ValueError("Limit must be at least 1")
        except:
            bot.reply_to(message, "❌ Invalid limit. Please provide a positive integer.")
            return
        
        target_input = args[2]
        try:
            if target_input.startswith('@'):
                user_info = bot.get_chat(target_input)
                target = user_info.id
            else:
                target = int(target_input)
        except:
            bot.reply_to(message, "❌ Invalid user specified")
            return
        
        db.custom_limits[target] = limit
        db.save_data()
        
        username, name = get_user_info(target)
        
        bot.reply_to(message,
            f"✨ <b>CUSTOM LIMIT SET SUCCESSFULLY!</b> ✨\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"📛 <b>Name:</b> {name}\n"
            f"🆔 <b>ID:</b> <code>{target}</code>\n"
            f"💎 <b>Daily Like Limit:</b> {limit}\n\n"
            f"This user can now send up to {limit} Account Like per day.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in add_custom_limit: {e}")
        bot.reply_to(message, "❌ Error processing command")

@bot.message_handler(commands=['rmremind'])
def remove_custom_limit(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message,
                "💎 <b>Remove Custom Limit Command</b> 💎\n\n"
                "<code>/rmremind &lt;user_id/@username&gt;</code>\n\n"
                "<b>Examples:</b>\n"
                "<code>/rmremind 123456789</code>\n"
                "<code>/rmremind @username</code>",
                parse_mode='HTML'
            )
            return
        
        target_input = args[1]
        try:
            if target_input.startswith('@'):
                user_info = bot.get_chat(target_input)
                target = user_info.id
            else:
                target = int(target_input)
        except:
            bot.reply_to(message, "❌ Invalid user specified")
            return
        
        if target in db.custom_limits:
            del db.custom_limits[target]
            db.save_data()
            
            username, name = get_user_info(target)
            
            bot.reply_to(message,
                f"✨ <b>CUSTOM LIMIT REMOVED SUCCESSFULLY!</b> ✨\n\n"
                f"👤 <b>User:</b> {username}\n"
                f"📛 <b>Name:</b> {name}\n"
                f"🆔 <b>ID:</b> <code>{target}</code>\n\n"
                f"This user's custom daily limit has been removed.",
                parse_mode='HTML'
            )
        else:
            bot.reply_to(message, "⚠️ This user doesn't have a custom limit set.")
            
    except Exception as e:
        logger.error(f"Error in remove_custom_limit: {e}")
        bot.reply_to(message, "❌ Error processing command")

@bot.message_handler(commands=['admin'])
def admin_commands(message):
    if not check_bot_active(message):
        return
    
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not authorized to use this command!")
        return
    
    admin_help = """
🔐 <b>GHOST X ADMIN COMMANDS</b> 🔐

💰 <b>Coin Management:</b>
<code>/addc &lt;amount&gt; &lt;user_id/username&gt;</code> - Add coins
<code>/dcn &lt;amount/all&gt; &lt;user_id/username&gt;</code> - Deduct coins
<code>/coins &lt;user_id/username&gt;</code> - Check balance

👑 <b>VIP Management:</b>
<code>/addvip &lt;duration&gt; &lt;user_id/username&gt;</code> - Add VIP
<code>/dvip &lt;user_id/username&gt;</code> - Remove VIP
<code>/vips</code> - List VIP users

📡 <b>Broadcasting:</b>
<code>/broadcast</code> - Broadcast to all users
<code>/modhu</code> - Official broadcast with header

🔌 <b>Bot Control:</b>
<code>/ghost-on</code> - Turn bot on
<code>/ghost-off</code> - Turn bot off
<code>/verification-on</code> - Enable verification system
<code>/verification-off</code> - Disable verification system
<code>/verification_video_on</code> - Enable verification video
<code>/verification_video_off</code> - Disable verification video

🎚️ <b>Custom Limits:</b>
<code>/addremind &lt;limit&gt; &lt;user_id/username&gt;</code> - Set custom daily like limit
<code>/rmremind &lt;user_id/username&gt;</code> - Remove custom limit

⚙️ <b>Other Commands:</b>
<code>/admin</code> - Show this menu
"""
    bot.reply_to(message, admin_help, parse_mode='HTML')

# ===================== USER COMMANDS =====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    if not check_bot_active(message):
        return
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('verify_'):
        handle_verification(message)
        return
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🌟 JOIN VIP GROUP", url=Config.GROUP_LINK))
    for channel in Config.CHANNELS:
        kb.add(InlineKeyboardButton(f"📢 JOIN {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
    kb.add(InlineKeyboardButton("🔗 JOIN ALL CHANNELS AT ONCE", url=Config.CHANNEL_JOIN_LINK))  # New join all button
    
    bot.reply_to(message,
        "✨ <b>🔥 WELCOME TO GHOST X VIP BOT 🔥</b> ✨\n\n"
        "💎 <b>Premium FF ID Services</b>\n"
        "⚡ Instant Like/Visit Delivery\n"
        "🔒 Secure VIP Network\n\n"
        "<b>🔗 JOIN OUR CHANNELS TO USE THE BOT:</b>\n"
        "⚠️ You must join all channels to access bot features\n"
        "Click below to join required channels:",
        reply_markup=kb,
        disable_web_page_preview=True
    )

@bot.message_handler(commands=['help'])
def handle_help(message):
    if not check_bot_active(message):
        return
    
    is_vip_user = is_vip(message.from_user.id)
    
    help_message = """
✨ <b>GHOST X VIP BOT HELP CENTER</b> ✨

🎮 <b>MAIN COMMANDS:</b>
╰┈➤ <code>/start</code> - Start the bot
╰┈➤ <code>/help</code> - Show this help
╰┈➤ <code>/coins</code> - Check your coins

💎 <b>VIP SERVICES:</b>
╰┈➤ <code>/like &lt;region&gt; &lt;uid&gt;</code> - Send likes
╰┈➤ <code>/visit &lt;region&gt; &lt;uid&gt;</code> - Send visits
╰┈➤ <code>/leaderboard &lt;region&gt; &lt;mode&gt;</code> - Show leaderboard (br/cs)
╰┈➤ <code>/bp_leaderboard</code> - Show Booyah Pass leaderboard

🌐 <b>REGION CODES:</b>
╰┈➤ <code>bd</code> - Bangladesh
╰┈➤ <code>ind</code> - Indonesia
╰┈➤ <code>ind</code> - India
╰┈➤ <code>br</code> - Brazil
╰┈➤ <code>pk</code> - Pakistan

🎮 <b>MODE CODES:</b>
╰┈➤ <code>br</code> - Battle Royale
╰┈➤ <code>cs</code> - Clash Squad

🔐 <b>VERIFICATION SYSTEM:</b>
1. Join required channels
2. Use /like or /visit
3. Complete verification
4. Earn 1 free credit

💰 <b>COIN SYSTEM:</b>
╰┈➤ Earn coins via verification
╰┈➤ Spend coins for services
╰┈➤ Check with /coins
""" + (f"""

🌟 <b>VIP MEMBER PERKS:</b>
╰┈➤ {Config.VIP_USER_DAILY_LIMIT} likes per day
╰┈➤ No cooldowns
╰┈➤ Priority support
""" if is_vip_user else f"""

🔮 <b>FREE USER LIMITS:</b>
╰┈➤ {Config.FREE_USER_DAILY_LIMIT} like per day
╰┈➤ Cooldowns apply
""") + """

📢 <b>SUPPORT:</b>
╰┈➤ Channel: @GST_X_STATUS
╰┈➤ Group: @GHOST_XTOOLS
╰┈➤ Owner: @GHOST_HELPLINE_BOT
"""
    bot.reply_to(message, help_message, parse_mode='HTML', disable_web_page_preview=True)

@bot.message_handler(commands=['leaderboard'])
def handle_leaderboard(message):
    if not check_bot_active(message):
        return
    
    db.all_users.add(message.from_user.id)
    
    if message.chat.type == "private":
        bot.reply_to(message, f"⚠️ VIP COMMAND ONLY WORKS IN OUR GROUP:\n{Config.GROUP_LINK}", disable_web_page_preview=True)
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message,
            "<b>💎 LEADERBOARD COMMAND USAGE</b>\n\n"
            "<code>/leaderboard &lt;region&gt; &lt;mode&gt;</code>\n\n"
            "<b>Regions:</b> bd, ind, br, pk, etc.\n"
            "<b>Modes:</b> br (Battle Royale), cs (Clash Squad)\n\n"
            "<b>Examples:</b>\n"
            "<code>/leaderboard bd br</code>\n"
            "<code>/leaderboard ind cs</code>",
            disable_web_page_preview=True
        )
        return
    
    region, mode = args[1], args[2].lower()
    
    if mode not in ['br', 'cs']:
        bot.reply_to(message, "❌ Invalid mode. Use 'br' for Battle Royale or 'cs' for Clash Squad")
        return
    
    msg = bot.reply_to(message, "⚡ FETCHING LEADERBOARD DATA...")
    
    api_result = call_leaderboard_api(mode, region)
    
    if api_result.get('error'):
        bot.edit_message_text(
            "❌ Failed to fetch leaderboard data. Please try again later.",
            message.chat.id,
            msg.message_id
        )
        return
    
    leaderboard_text = format_leaderboard(api_result, mode)
    
    bot.edit_message_text(
        leaderboard_text,
        message.chat.id,
        msg.message_id,
        parse_mode='HTML'
    )

@bot.message_handler(commands=['bp_leaderboard'])
def handle_bp_leaderboard(message):
    if not check_bot_active(message):
        return
    
    db.all_users.add(message.from_user.id)
    
    if message.chat.type == "private":
        bot.reply_to(message, f"⚠️ VIP COMMAND ONLY WORKS IN OUR GROUP:\n{Config.GROUP_LINK}", disable_web_page_preview=True)
        return
    
    msg = bot.reply_to(message, "⚡ FETCHING BOOYAH PASS LEADERBOARD...")
    
    api_result = call_leaderboard_api("bp")
    
    if api_result.get('error'):
        bot.edit_message_text(
            "❌ Failed to fetch leaderboard data. Please try again later.",
            message.chat.id,
            msg.message_id
        )
        return
    
    leaderboard_text = format_leaderboard(api_result, "bp")
    
    bot.edit_message_text(
        leaderboard_text,
        message.chat.id,
        msg.message_id,
        parse_mode='HTML'
    )

@bot.message_handler(commands=['like'])
def handle_like(message):
    if not check_bot_active(message):
        return
    
    db.all_users.add(message.from_user.id)
    
    if message.chat.type == "private":
        bot.reply_to(message, f"⚠️ VIP COMMAND ONLY WORKS IN OUR GROUP:\n{Config.GROUP_LINK}", disable_web_page_preview=True)
        return
    
    # Check daily limit
    user_id = message.from_user.id
    can_send, remaining = db.can_send_like(user_id)
    
    if not can_send:
        reset_time = get_next_reset_time()
        if is_vip(user_id) or user_id in db.custom_limits:
            bot.reply_to(message, 
                f"⚠️ <b>DAILY LIMIT REACHED</b>\n\n"
                f"You have reached your daily limit for likes.\n"
                f"Please wait until {reset_time} for your limit to reset.\n\n"
                f"💎 <b>Current Status:</b> {'VIP' if is_vip(user_id) else 'Custom Limit'}",
                disable_web_page_preview=True
            )
        else:
            bot.reply_to(message, 
                f"⚠️ <b>DAILY LIMIT REACHED</b>\n\n"
                f"You have used your 1 free like for today.\n"
                f"Your limit will reset at {reset_time}.\n\n"
                f"💎 <b>Upgrade to VIP</b> to get {Config.VIP_USER_DAILY_LIMIT} likes per day!\n"
                f"Contact @GHOST_HELPLINE_BOT for VIP membership.",
                disable_web_page_preview=True
            )
        return
    
    if message.from_user.id in db.pending_requests:
        try:
            old_msg = db.pending_requests[message.from_user.id]['message']
            if old_msg and old_msg.message_id != message.message_id:
                try:
                    bot.delete_message(old_msg.chat.id, old_msg.message_id)
                except:
                    pass
        except:
            pass
    
    not_joined = is_subscribed(message.from_user.id)
    if not_joined:
        kb = InlineKeyboardMarkup()
        for channel in not_joined:
            kb.add(InlineKeyboardButton(f"📢 JOIN {channel} (REQUIRED)", url=f"https://t.me/{channel.replace('@', '')}"))
        kb.add(InlineKeyboardButton("🔗 JOIN ALL CHANNELS AT ONCE", url=Config.CHANNEL_JOIN_LINK))  # New join all button
        kb.add(InlineKeyboardButton("🔓 VERIFY JOINING", callback_data=f"verify_join:{message.from_user.id}:like"))
        
        sent_msg = bot.reply_to(message, 
            "<b>🔒 CHANNEL JOIN REQUIRED</b>\n\n"
            "⚠️ You must join all our channels to use this bot!\n"
            "Click the buttons below to join required channels:",
            reply_markup=kb,
            disable_web_page_preview=True)
        
        db.pending_requests[message.from_user.id] = {
            'message': sent_msg,
            'type': 'like',
            'region': None,
            'uid': None
        }
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message,
            "<b>💎 VIP LIKE COMMAND USAGE</b>\n\n"
            "<code>/like &lt;region&gt; &lt;uid&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "<code>/like bd 123456789</code>\n"
            "<code>/like id 987654321</code>",
            disable_web_page_preview=True
        )
        return
    
    region, uid = args[1], args[2]
    
    user_id = message.from_user.id
    
    # Check if verification is required
    if db.verification_enabled and not is_vip(user_id) and db.verification_credits.get(user_id, 0) <= 0:
        verification_msg = create_verification_message(user_id, region, uid, 'like')
        if Config.VERIFICATION_VIDEO_ENABLED:
            sent_msg = bot.send_video(
                chat_id=message.chat.id,
                video=verification_msg['video'],
                caption=verification_msg['caption'],
                reply_markup=verification_msg['reply_markup'],
                reply_to_message_id=message.message_id
            )
        else:
            sent_msg = bot.reply_to(message,
                verification_msg['text'],
                reply_markup=verification_msg['reply_markup'],
                disable_web_page_preview=True
            )
        
        db.pending_requests[user_id]['message'] = sent_msg
        db.save_data()
        return
    
    # If verification is not required or user has credits/VIP
    process_like(message, region, uid)

@bot.message_handler(commands=['visit'])
def handle_visit(message):
    if not check_bot_active(message):
        return
    
    db.all_users.add(message.from_user.id)
    
    if message.chat.type == "private":
        bot.reply_to(message, f"⚠️ VIP COMMAND ONLY WORKS IN OUR GROUP:\n{Config.GROUP_LINK}", disable_web_page_preview=True)
        return
    
    if message.from_user.id in db.pending_requests:
        try:
            old_msg = db.pending_requests[message.from_user.id]['message']
            if old_msg and old_msg.message_id != message.message_id:
                try:
                    bot.delete_message(old_msg.chat.id, old_msg.message_id)
                except:
                    pass
        except:
            pass
    
    not_joined = is_subscribed(message.from_user.id)
    if not_joined:
        kb = InlineKeyboardMarkup()
        for channel in not_joined:
            kb.add(InlineKeyboardButton(f"📢 JOIN {channel} (REQUIRED)", url=f"https://t.me/{channel.replace('@', '')}"))
        kb.add(InlineKeyboardButton("🔗 JOIN ALL CHANNELS AT ONCE", url=Config.CHANNEL_JOIN_LINK))  # New join all button
        kb.add(InlineKeyboardButton("🔓 VERIFY JOINING", callback_data=f"verify_join:{message.from_user.id}:visit"))
        
        sent_msg = bot.reply_to(message, 
            "<b>🔒 CHANNEL JOIN REQUIRED</b>\n\n"
            "⚠️ You must join all our channels to use this bot!\n"
            "Click the buttons below to join required channels:",
            reply_markup=kb,
            disable_web_page_preview=True)
        
        db.pending_requests[message.from_user.id] = {
            'message': sent_msg,
            'type': 'visit',
            'region': None,
            'uid': None
        }
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message,
            "<b>👑 VIP VISIT COMMAND USAGE</b>\n\n"
            "<code>/visit &lt;region&gt; &lt;uid&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "<code>/visit bd 123456789</code>\n"
            "<code>/visit id 987654321</code>",
            disable_web_page_preview=True
        )
        return
    
    region, uid = args[1], args[2]
    
    user_id = message.from_user.id
    
    if not is_vip(user_id):
        last_visit = db.visit_cooldowns.get(user_id, 0)
        elapsed = time.time() - last_visit
        if elapsed < Config.VISIT_COOLDOWN:
            remaining = int(Config.VISIT_COOLDOWN - elapsed)
            bot.reply_to(message, f"⏳ Please wait {remaining} seconds before sending another visit.\n💎 Become VIP for no cooldown!")
            return
    
    # Check if verification is required
    if db.verification_enabled and not is_vip(user_id) and db.verification_credits.get(user_id, 0) <= 0:
        verification_msg = create_verification_message(user_id, region, uid, 'visit')
        if Config.VERIFICATION_VIDEO_ENABLED:
            sent_msg = bot.send_video(
                chat_id=message.chat.id,
                video=verification_msg['video'],
                caption=verification_msg['caption'],
                reply_markup=verification_msg['reply_markup'],
                reply_to_message_id=message.message_id
            )
        else:
            sent_msg = bot.reply_to(message,
                verification_msg['text'],
                reply_markup=verification_msg['reply_markup'],
                disable_web_page_preview=True
            )
        
        db.pending_requests[user_id]['message'] = sent_msg
        db.save_data()
        return
    
    # If verification is not required or user has credits/VIP
    process_visit(message, region, uid)

def process_like(message, region, uid, original_credits=None):
    msg = bot.reply_to(message, "⚡ PROCESSING VIP REQUEST...")
    
    steps = [
        "🔐 VERIFYING VIP ACCESS...",
        "🌐 CONNECTING TO SERVER...",
        "💎 PROCESSING REQUEST...",
        "✅ FINALIZING TRANSACTION..."
    ]
    
    for step in steps:
        try:
            bot.edit_message_text(step, message.chat.id, msg.message_id)
            time.sleep(1.2)
        except Exception as e:
            logger.error(f"Error updating like progress: {e}")
    
    api_result = call_like_api(region, uid)
    user_id = message.from_user.id
    
    status = api_result.get('status', 0)
    
    # Only increment like count if the like was successful (status 1)
    if status == 1:
        db.increment_like_count(user_id)
    elif status == 0:  # If like failed, restore credits if applicable
        if original_credits is not None and user_id not in db.vip_users:
            db.verification_credits[user_id] = original_credits
            db.save_data()
    
    try:
        if status == 1:
            likes_given = int(api_result.get('LikesGivenByAPI', 0))
            likes_before = int(api_result.get('LikesbeforeCommand', 0))
            likes_after = int(api_result.get('LikesafterCommand', 0))
            
            bot.send_video(
                chat_id=message.chat.id,
                video=Config.SUCCESS_VIDEO,
                caption=(
                    "<b>💎 VIP LIKE SUCCESSFULLY DELIVERED!</b>\n\n"
                    f"👑 <b>Player:</b> {api_result.get('PlayerNickname', 'VIP USER')}\n"
                    f"🆔 <b>UID:</b> {api_result.get('UID', uid)}\n"
                    f"🌍 <b>Region:</b> {region.upper()}\n\n"
                    f"💖 <b>Likes Sent:</b> {likes_given}\n"
                    f"📊 <b>Before:</b> {likes_before} | <b>After:</b> {likes_after}\n"
                    f"🔥 <b>Total Likes Now:</b> {likes_after}\n\n"
                    f"🌟 <b>Status:</b> {'VIP MEMBER' if is_vip(user_id) else f'CREDITS LEFT: {db.verification_credits.get(user_id, 0)}'}\n\n"
                    f"Join @GST_X_STATUS for updates"
                ),
                reply_to_message_id=message.message_id
            )
            
        elif status == 2:
            bot.send_video(
                chat_id=message.chat.id,
                video=Config.SUCCESS_VIDEO,
                caption=(
                    "<b>⚠️ ACCOUNT ALREADY LIKED</b>\n\n"
                    f"👑 <b>Player:</b> {api_result.get('PlayerNickname', 'VIP USER')}\n"
                    f"🆔 <b>UID:</b> {api_result.get('UID', uid)}\n"
                    f"🌍 <b>Region:</b> {region.upper()}\n\n"
                    f"💖 <b>Current Likes:</b> {api_result.get('LikesafterCommand')}\n\n"
                    "Your credit has been restored.\n\n"
                    f"Join @GST_X_STATUS for support"
                ),
                reply_to_message_id=message.message_id
            )
            
        else:
            bot.send_video(
                chat_id=message.chat.id,
                video=Config.SUCCESS_VIDEO,
                caption=(
                    "<b>❌ LIKE REQUEST FAILED</b>\n\n"
                    f"🆔 <b>UID:</b> {uid}\n"
                    f"🌍 <b>Region:</b> {region.upper()}\n\n"
                    "Please check the UID and region and try again.\n\n"
                    f"Join @GST_X_STATUS for support"
                ),
                reply_to_message_id=message.message_id
            )
            
        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Like response error: {e}")
        try:
            bot.edit_message_text(
                f"<b>💎 VIP LIKE PROCESSED</b>\n"
                f"🆔 <b>UID:</b> {uid}\n"
                f"🌍 <b>Region:</b> {region.upper()}\n"
                f"💖 <b>Status:</b> {'SUCCESS' if status == 1 else 'ALREADY LIKED' if status == 2 else 'FAILED'}",
                message.chat.id,
                msg.message_id
            )
        except:
            pass

def process_visit(message, region, uid, original_credits=None):
    msg = bot.reply_to(message, "⚡ PROCESSING VISIT REQUEST...")
    
    steps = [
        "🔐 VERIFYING VIP ACCESS...",
        "🌐 CONNECTING TO SERVER...",
        "👀 SENDING VISITS...",
        "✅ FINALIZING TRANSACTION..."
    ]
    
    for step in steps:
        try:
            bot.edit_message_text(step, message.chat.id, msg.message_id)
            time.sleep(1.2)
        except Exception as e:
            logger.error(f"Error updating visit progress: {e}")
    
    api_result = call_visit_api(region, uid)
    user_id = message.from_user.id
    
    if not is_vip(user_id):
        db.visit_cooldowns[user_id] = time.time()
        db.save_data()
    
    try:
        if "nickname" in api_result:
            bot.send_video(
                chat_id=message.chat.id,
                video=Config.SUCCESS_VIDEO,
                caption=(
                    "<b>👑 VIP VISIT SUCCESSFULLY DELIVERED!</b>\n\n"
                    f"🔰 <b>FF NAME:</b> {api_result.get('nickname', 'VIP USER')}\n"
                    f"🆔 <b>UID:</b> {api_result.get('uid', uid)}\n"
                    f"📊 <b>LEVEL:</b> {api_result.get('level', 'N/A')}\n"
                    f"🌍 <b>REGION:</b> {region.upper()}\n"
                    f"✅ <b>SUCCESS:</b> {api_result.get('success', 0)}\n"
                    f"❌ <b>FAILED:</b> {api_result.get('fail', 0)}\n\n"
                    f"🌟 <b>Status:</b> {'VIP MEMBER' if is_vip(user_id) else f'CREDITS LEFT: {db.verification_credits.get(user_id, 0)}'}\n\n"
                    f"Join @GST_X_STATUS for updates"
                ),
                reply_to_message_id=message.message_id
            )
        else:
            if original_credits is not None and user_id not in db.vip_users:
                db.verification_credits[user_id] = original_credits
                db.save_data()
            
            bot.send_video(
                chat_id=message.chat.id,
                video=Config.SUCCESS_VIDEO,
                caption=(
                    "<b>❌ VISIT REQUEST FAILED</b>\n\n"
                    f"🆔 <b>UID:</b> {uid}\n"
                    f"🌍 <b>Region:</b> {region.upper()}\n\n"
                    "Please check the UID and region and try again.\n\n"
                    f"Join @GST_X_STATUS for support"
                ),
                reply_to_message_id=message.message_id
            )
            
        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Visit response error: {e}")
        try:
            bot.edit_message_text(
                f"<b>👑 VIP VISIT PROCESSED</b>\n"
                f"🆔 <b>UID:</b> {uid}\n"
                f"🌍 <b>Region:</b> {region.upper()}\n"
                f"👀 <b>Status:</b> {'SUCCESS' if 'nickname' in api_result else 'FAILED'}",
                message.chat.id,
                msg.message_id
            )
        except:
            pass

def handle_verification(message):
    try:
        token = message.text.split()[1][7:]
        user_id = message.from_user.id
        
        if token in db.used_tokens:
            if db.token_to_user.get(token) == user_id:
                if user_id in db.pending_requests:
                    req = db.pending_requests[user_id]
                    try:
                        if req['message']:
                            bot.delete_message(req['message'].chat.id, req['message'].message_id)
                    except:
                        pass
                    
                    if req['type'] == 'like':
                        process_like(req['message'], req['region'], req['uid'])
                    elif req['type'] == 'visit':
                        process_visit(req['message'], req['region'], req['uid'])
                    del db.pending_requests[user_id]
                    return
                
                bot.reply_to(message, 
                    "<b>✅ VERIFICATION ALREADY COMPLETED</b>\n\n"
                    "You've already claimed credit from this link!\n\n"
                    f"💎 <b>Current Credits:</b> {db.verification_credits.get(user_id, 0)}")
            else:
                bot.reply_to(message, 
                    "<b>⚠️ LINK ALREADY USED</b>\n\n"
                    "This verification link was already used by another user!")
            return
        
        if db.token_to_user.get(token) != user_id:
            bot.reply_to(message, 
                "⚠️ <b>INVALID VERIFICATION LINK</b>\n\n"
                "This verification link doesn't belong to you!")
            return
        
        db.used_tokens.add(token)
        db.verification_credits[user_id] = db.verification_credits.get(user_id, 0) + 1
        db.user_coins[user_id] = db.user_coins.get(user_id, 0) + 1
        db.user_last_verification[user_id] = time.time()
        db.all_users.add(user_id)
        db.save_data()
        
        if user_id in db.pending_requests:
            req = db.pending_requests[user_id]
            try:
                if req['message']:
                    bot.delete_message(req['message'].chat.id, req['message'].message_id)
            except:
                pass
            
            if req['type'] == 'like':
                process_like(req['message'], req['region'], req['uid'])
            elif req['type'] == 'visit':
                process_visit(req['message'], req['region'], req['uid'])
            del db.pending_requests[user_id]
            return
        
        bot.reply_to(message,
            "✨ <b>✅ VERIFICATION SUCCESSFUL!</b> ✨\n\n"
            f"💎 <b>Credit Received:</b> 1 VIP credit\n"
            f"🪙 <b>Coin Bonus:</b> 1 Ghost Coin\n\n"
            f"📊 <b>Current Balance:</b>\n"
            f"╰┈➤ <b>VIP Credits:</b> {db.verification_credits.get(user_id, 0)}\n"
            f"╰┈➤ <b>Ghost Coins:</b> {db.user_coins.get(user_id, 0)}\n\n"
            f"Use /like or /visit in {Config.GROUP_LINK} to send likes/visits\n\n"
            f"🌟 Check your balance with /coins",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Verification error: {e}")
        bot.reply_to(message, 
            "⚠️ <b>VERIFICATION SUCCESS</b>\n\n"
            "PLEASE SEND COMMAND ON @GHOST_XTOOLS GROUP 💥")

@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_join'))
def handle_verify_join(call):
    try:
        data_parts = call.data.split(':')
        user_id = int(data_parts[1])
        command_type = data_parts[2] if len(data_parts) > 2 else 'like'
        
        not_joined = is_subscribed(user_id)
        
        if not_joined:
            kb = InlineKeyboardMarkup()
            for channel in not_joined:
                kb.add(InlineKeyboardButton(f"📢 JOIN {channel} (REQUIRED)", url=f"https://t.me/{channel.replace('@', '')}"))
            kb.add(InlineKeyboardButton("🔗 JOIN ALL CHANNELS AT ONCE", url=Config.CHANNEL_JOIN_LINK))  # New join all button
            kb.add(InlineKeyboardButton("🔓 VERIFY JOINING", callback_data=f"verify_join:{user_id}:{command_type}"))
            
            try:
                bot.answer_callback_query(call.id, "⚠️ Please join all channels first!", show_alert=True)
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="<b>🔒 CHANNEL JOIN REQUIRED</b>\n\n"
                         "⚠️ You must join all our channels to use this bot!\n"
                         "Click the buttons below to join required channels:",
                    reply_markup=kb
                )
            except Exception as e:
                logger.error(f"Error in verify join: {e}")
        else:
            try:
                bot.answer_callback_query(call.id, f"✅ Verification successful! You can now use /{command_type}", show_alert=True)
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"Error deleting verify join message: {e}")
    except Exception as e:
        logger.error(f"Error in verify_join handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('credit'))
def handle_credit(call):
    try:
        _, user_id, region, uid, command_type = call.data.split(':')
        user_id = int(user_id)
        
        not_joined = is_subscribed(user_id)    
        if not_joined:
            kb = InlineKeyboardMarkup()
            for channel in not_joined:
                kb.add(InlineKeyboardButton(f"📢 JOIN {channel} (REQUIRED)", url=f"https://t.me/{channel.replace('@', '')}"))
            kb.add(InlineKeyboardButton("🔗 JOIN ALL CHANNELS AT ONCE", url=Config.CHANNEL_JOIN_LINK))  # New join all button
            kb.add(InlineKeyboardButton("🔓 VERIFY JOINING", callback_data=f"verify_join:{user_id}:{command_type}"))
            
            bot.answer_callback_query(call.id, "⚠️ Please join all channels first!", show_alert=True)
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="<b>🔒 CHANNEL JOIN REQUIRED</b>\n\n"
                         "⚠️ You must join all our channels to use this bot!\n"
                         "Click the buttons below to join required channels:",
                    reply_markup=kb
                )
            except:
                pass
            return
        
        elapsed = time.time() - db.user_last_verification.get(user_id, 0)
        
        if elapsed < Config.VERIFICATION_COOLDOWN:
            remaining = int((Config.VERIFICATION_COOLDOWN - elapsed) / 60)
            bot.answer_callback_query(call.id, f"⏳ Please wait {remaining} minutes before verifying again", show_alert=True)
            return
        
        verification_msg = create_verification_message(user_id, region, uid, command_type)
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        if Config.VERIFICATION_VIDEO_ENABLED:
            sent_msg = bot.send_video(
                chat_id=call.message.chat.id,
                video=verification_msg['video'],
                caption=verification_msg['caption'],
                reply_markup=verification_msg['reply_markup']
            )
        else:
            sent_msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=verification_msg['text'],
                reply_markup=verification_msg['reply_markup'],
                disable_web_page_preview=True
            )
        
        db.pending_requests[user_id]['message'] = sent_msg
        db.save_data()
        
        bot.answer_callback_query(call.id, "Verification link generated!")
        
    except Exception as e:
        logger.error(f"Credit error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Error generating link. Please try again.", show_alert=True)

@bot.message_handler(func=lambda message: message.text.startswith('Get ') and message.chat.type != "private")
def handle_freefire_info(message):
    if not check_bot_active(message):
        return
    
    text = message.text
    parts = text.split()
    if len(parts) != 3:
        bot.reply_to(message, "Use: Get <region> <uid>")
        return

    region, uid = parts[1], parts[2]
    msg = bot.reply_to(message, f"Fetching info for UID `{uid}`...")

    data = get_profile_info(uid, region)
    if not data:
        bot.edit_message_text("❌ Failed to fetch data. Try again.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    pinfo = data.get("player_info", {})
    basic = pinfo.get("basicInfo", {})
    social = pinfo.get("socialInfo", {})
    pet = pinfo.get("petInfo", {})
    credit = pinfo.get("creditScoreInfo", {})
    profile = pinfo.get("profileInfo", {})

    created_at = format_timestamp(basic.get("createAt", 0))
    last_login = format_timestamp(basic.get("lastLoginAt", 0))
    signature = social.get("signature", "No Signature")
    elite_pass = "Yes" if basic.get("hasElitePass", False) else "No"
    equipped_skills = profile.get("equipedSkills", [])
    equipped_skills_str = ", ".join(str(s) for s in equipped_skills) if equipped_skills else "N/A"
    clothes = profile.get("clothes", [])
    clothes_str = ", ".join(str(c) for c in clothes) if clothes else "N/A"

    msg_text = (
        f"┌🧑‍💻 ACCOUNT BASIC INFO\n"
        f"├─ Name: {basic.get('nickname', 'Unknown')}\n"
        f"├─ UID: {basic.get('accountId', uid)}\n"
        f"├─ Level: {basic.get('level', 'N/A')} (Exp: {basic.get('exp', 'N/A')})\n"
        f"├─ Region: {basic.get('region', region)}\n"
        f"├─ Likes: {basic.get('liked', 'N/A')}\n"
        f"├─ Honor Score: {credit.get('creditScore', 'N/A')}\n"
        f"├─ Title: {basic.get('badgeId', 'N/A')}\n"
        f"└─ Signature: {signature}\n\n"

        f"┌🎮 ACCOUNT ACTIVITY\n"
        f"├─ Most Recent OB: {basic.get('releaseVersion', 'N/A')}\n"
        f"├─ Booyah Pass: {elite_pass}\n"
        f"├─ Current BP Badges: {basic.get('badgeCnt', 'N/A')}\n"
        f"├─ BR Rank: {basic.get('rank', 'N/A')}\n"
        f"├─ CS Points: {basic.get('csRankingPoints', 'N/A')}\n"
        f"├─ Created At: {created_at}\n"
        f"└─ Last Login: {last_login}\n\n"

        f"┌👕 ACCOUNT OVERVIEW\n"
        f"├─ Avatar ID: {basic.get('headPic', 'Default')}\n"
        f"├─ Banner ID: {basic.get('bannerId', 'Default')}\n"
        f"├─ Equipped Skills: {equipped_skills_str}\n"
        f"├─ Outfits: {clothes_str}\n\n"

        f"┌🐾 PET DETAILS\n"
        f"├─ Equipped?: {'Yes' if pet.get('isSelected', False) else 'No'}\n"
        f"├─ Pet ID: {pet.get('id', 'N/A')}\n"
        f"├─ Pet Exp: {pet.get('exp', 'N/A')}\n"
        f"└─ Pet Level: {pet.get('level', 'N/A')}\n"
    )

    bot.edit_message_text(msg_text, chat_id=message.chat.id, message_id=msg.message_id)

    banner_url = f"{Config.BANNER_API_URL}?uid={uid}&region={region}"
    outfit_url = f"{Config.OUTFIT_API_URL}?uid={uid}&region={region}&key=99day"

    try:
        bot.send_photo(message.chat.id, banner_url, caption="🖼️ BANNER IMAGE")
    except Exception as e:
        logger.error(f"Failed to send banner image: {e}")

    try:
        bot.send_photo(message.chat.id, outfit_url, caption="🧥 OUTFIT IMAGE")
    except Exception as e:
        logger.error(f"Failed to send outfit image: {e}")

# Schedule daily reset
def schedule_daily_reset():
    while True:
        now = datetime.now()
        # Check if it's time to reset (after 7 AM)
        if now.hour >= Config.RESET_TIME:
            reset_date = now.strftime('%Y-%m-%d')
        else:
            reset_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Check if we need to reset counts
        for user_id in list(db.user_daily_likes.keys()):
            if db.user_daily_likes[user_id]['date'] != reset_date:
                db.user_daily_likes[user_id] = {'count': 0, 'date': now.strftime('%Y-%m-%d')}
                db.save_data()
        
        # Sleep for 1 hour before checking again
        time.sleep(3600)

# Start the reset scheduler in a separate thread
import threading
reset_thread = threading.Thread(target=schedule_daily_reset)
reset_thread.daemon = True
reset_thread.start()

if __name__ == "__main__":
    print("✨ GHOST X VIP BOT IS RUNNING... ✨")
    bot.infinity_polling()