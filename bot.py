# bot.py - SADE BOT (SADECE TOP5 ve ID)

import telebot
import os
import re
import datetime
import time
from telebot import types

from config import BOT_TOKEN, ALLOWED_GROUP_ID, IRAQ_TIMEZONE
from database import Database

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

# ============================================
# YARDIMCI FONKSİYONLAR
# ============================================

def is_allowed_group(message):
    if message.chat.type == 'private':
        return False
    return message.chat.id == ALLOWED_GROUP_ID

def get_mention_html(user_id, username, first_name):
    if username:
        return f"@{username}"
    else:
        return f"<a href='tg://user?id={user_id}'>{first_name}</a>"

def clean_bio(bio):
    if not bio:
        return "🚫 Bio yok"
    bio = re.sub(r'https?://\S+', '', bio)
    bio = re.sub(r'www\.\S+', '', bio)
    bio = re.sub(r't\.me/\S+', '', bio)
    bio = re.sub(r'@\S+', '', bio)
    bio = re.sub(r'\s+', ' ', bio)
    bio = bio.strip()
    if not bio:
        return "🚫 Bio yok"
    return bio

def send_daily_top5():
    """Günlük en çok konuşan 5 kişiyi gönder (her gün 12:00'de)"""
    try:
        today = datetime.datetime.now().date()
        if self.is_postgres:
            self.cursor.execute("""
                SELECT ds.user_id, u.username, u.first_name, ds.message_count
                FROM daily_stats ds JOIN users u ON ds.user_id = u.user_id
                WHERE ds.date = %s ORDER BY ds.message_count DESC LIMIT 5
            """, (today,))
        else:
            self.cursor.execute("""
                SELECT ds.user_id, u.username, u.first_name, ds.message_count
                FROM daily_stats ds JOIN users u ON ds.user_id = u.user_id
                WHERE ds.date = ? ORDER BY ds.message_count DESC LIMIT 5
            """, (today,))
        
        top_users = self.cursor.fetchall()
        
        if not top_users:
            message = "📊 **هیچ نامەیەک نەهاتە** ئەڤروژێ"
        else:
            message = "🏆 **ئەو کەسێن ژ هەمیان پتر نامە رێکرین د روژێ دا** 🏆\n\n"
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            
            for i, user in enumerate(top_users[:5]):
                user_id, username, first_name, msg_count = user
                if username:
                    name = f"@{username}"
                else:
                    name = f"<a href='tg://user?id={user_id}'>{first_name}</a>"
                message += f"{medals[i]} {name} - {msg_count} نامە\n"
        
        bot.send_message(ALLOWED_GROUP_ID, message, parse_mode='HTML')
        print("✅ Günlük top5 raporu gönderildi")
        
    except Exception as e:
        print(f"❌ Günlük rapor hatası: {e}")

# ============================================
# KOMUTLAR
# ============================================

@bot.message_handler(commands=['top5'])
def cmd_top5(message):
    """Günün en çok konuşan 5 kişisi"""
    try:
        if not is_allowed_group(message):
            bot.reply_to(message, "🚫 ئەڤ بوتە تنێ د گروپێ تایبەت دا کار دکت")
            return
        
        today = datetime.datetime.now().date()
        if db.is_postgres:
            db.cursor.execute("""
                SELECT ds.user_id, u.username, u.first_name, ds.message_count
                FROM daily_stats ds JOIN users u ON ds.user_id = u.user_id
                WHERE ds.date = %s ORDER BY ds.message_count DESC LIMIT 5
            """, (today,))
        else:
            db.cursor.execute("""
                SELECT ds.user_id, u.username, u.first_name, ds.message_count
                FROM daily_stats ds JOIN users u ON ds.user_id = u.user_id
                WHERE ds.date = ? ORDER BY ds.message_count DESC LIMIT 5
            """, (today,))
        
        top_users = db.cursor.fetchall()
        
        if not top_users:
            msg = "📊 **هیچ نامەیەک نەهاتە** ئەڤروژێ"
        else:
            msg = "🏆 **ئەو کەسێن ژ هەمیان پتر نامە رێکرین د روژێ دا** 🏆\n\n"
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            
            for i, user in enumerate(top_users[:5]):
                user_id, username, first_name, msg_count = user
                if username:
                    name = f"@{username}"
                else:
                    name = f"<a href='tg://user?id={user_id}'>{first_name}</a>"
                msg += f"{medals[i]} {name} - {msg_count} نامە\n"
        
        bot.reply_to(message, msg, parse_mode='HTML')
        
    except Exception as e:
        print(f"❌ top5 hatası: {e}")
        bot.reply_to(message, "❌ خەلەتیەک چێبی دوبارە هەولبدە")

@bot.message_handler(func=lambda message: message.text and message.text.lower() in ['id', 'ايدي', 'ایدی', 'ıd'])
def cmd_id(message):
    """Kullanıcı bilgilerini göster (profil fotoğraflı)"""
    try:
        if not is_allowed_group(message):
            return
        
        user = message.from_user
        user_id = user.id
        
        db.add_user(user_id, user.username, user.first_name, user.last_name)
        stats = db.get_user_stats(user_id)
        
        if not stats:
            bot.reply_to(message, "👤 ئەندام نەهاتە دیتن")
            return
        
        username, first_name, total_messages, negative_points, last_date, joined_date = stats
        
        user_lang = user.language_code or "bilinmiyor"
        joined_date_str = joined_date[:10] if joined_date else "bilinmiyor"
        
        bio = ""
        try:
            user_profile = bot.get_chat(user_id)
            if hasattr(user_profile, 'bio') and user_profile.bio:
                bio = clean_bio(user_profile.bio)
            else:
                bio = "🚫 Bio yok"
        except Exception:
            bio = "🚫 Bio alınamadı"
        
        name_mention = f"<a href='tg://user?id={user_id}'>{first_name if first_name else 'بێ ناف'}</a>"
        user_text = f"@{username}" if username else "❌"
        
        caption = f"𖤓 𝐧𝐚𝐦𝐞 {name_mention}\n"
        caption += f"𖤓 𝐮𝐬𝐞𝐫 {user_text}\n"
        caption += f"𖤓 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 {total_messages}\n"
        caption += f"𖤓 𝐥𝐞𝐧𝐠 {user_lang}\n"
        caption += f"𖤓 𝐭𝐢𝐦𝐞 {joined_date_str}\n"
        caption += f"𖤓 𝐢𝐝 <code>{user_id}</code>\n"
        caption += f"𖤓 𝐛𝐢𝐨 {bio}"
        
        try:
            photos = bot.get_user_profile_photos(user_id, limit=1)
            if photos and photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                bot.send_photo(message.chat.id, file_id, caption=caption, parse_mode='HTML')
            else:
                bot.send_message(message.chat.id, caption, parse_mode='HTML')
        except:
            bot.send_message(message.chat.id, caption, parse_mode='HTML')
        
    except Exception as e:
        print(f"❌ id komutu hatası: {e}")
        bot.reply_to(message, "❌ خەلەتیەک چێبی")

# ============================================
# MESAJ İŞLEYİCİ
# ============================================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_messages(message):
    """Normal mesajları işle"""
    try:
        if not is_allowed_group(message):
            return
        
        if message.text and message.text.startswith('/'):
            command = message.text.split()[0].lower()
            if command in ['/top5']:
                return
        
        user = message.from_user
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        db.update_user_activity(user.id)
        
    except Exception as e:
        print(f"❌ handle_messages hatası: {e}")

# ============================================
# GRUP OLAYLARI
# ============================================
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    try:
        if not is_allowed_group(message):
            return
        
        for new_member in message.new_chat_members:
            if new_member.id == bot.get_me().id:
                bot.reply_to(message, "🔰 بوت داتایێن گروپی مە.\n/top5 - ئەو کەسێن ژ هەمیان پتر نامە رێکرین\nid - زانیاریێن کەسی")
                print("✅ Bot gruba eklendi!")
            else:
                db.add_user(new_member.id, new_member.username, new_member.first_name, new_member.last_name)
                print(f"✅ Yeni üye: {new_member.first_name}")
    except Exception as e:
        print(f"❌ new_member hatası: {e}")

@bot.message_handler(content_types=['left_chat_member'])
def handle_left_member(message):
    try:
        if not is_allowed_group(message):
            return
        if message.left_chat_member:
            user_id = message.left_chat_member.id
            if user_id != bot.get_me().id:
                db.remove_user(user_id)
                print(f"❌ Üye ayrıldı ve silindi: {user_id}")
    except Exception as e:
        print(f"❌ left_member hatası: {e}")

# ============================================
# GÜNLÜK RAPOR ZAMANLAYICI
# ============================================
import threading
import schedule

def run_scheduler():
    schedule.every().day.at("12:00").do(send_daily_top5)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler():
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("⏰ Günlük rapor zamanlayıcı başlatıldı (her gün 12:00)")

# ============================================
# BOTU BAŞLAT
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 SADE BOT BAŞLATILIYOR...")
    print("=" * 50)
    print(f"🔑 Token: {BOT_TOKEN[:10] if BOT_TOKEN else 'YOK'}...")
    print(f"👥 Grup ID: {ALLOWED_GROUP_ID}")
    print("-" * 50)
    print("✅ KOMUTLAR:")
    print("   • /top5 - Günün en çok konuşan 5 kişisi")
    print("   • id, ايدي, ایدی - Kullanıcı bilgileri")
    print("-" * 50)
    
    # Zamanlayıcıyı başlat
    start_scheduler()
    
    print("🚀 Polling başlıyor...")
    print("=" * 50)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Polling hatası: {e}")
        time.sleep(5)
