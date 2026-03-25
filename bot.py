# bot.py - ANA BOT DOSYASI

import telebot
import os
import re
import datetime
import time
import threading
from telebot import types

from config import BOT_TOKEN, ALLOWED_GROUP_ID, IRAQ_TIMEZONE
from database import Database
from scheduler import start_scheduler

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()
admin_cache = set()

class BadiniTranslations:
    @staticmethod
    def test_report(is_active, total_users, users_with_negatives, last_check, db_status, notified_count):
        return f"""📊 **راپورا بوتی**

🤖 **بوت اکتیڤە:** {'بەلێ' if is_active else 'نەخێر'}
👥 **متابعا انداما:** {total_users}
⚠️ **ئەو کەسێن ینزار هەین:** {users_with_negatives}
⏰ **دوماهیک کنترول:** {last_check}
💾 **داتا:** {'گرێدایە' if db_status else 'نە گرێدایە'}
🔔 **ئەو کەسێت هاتین تاکرن د 24 سعەتان دا:** {notified_count} کەس"""
    
    @staticmethod
    def negative_list_title():
        return "⚠️ **ئەو کەسێن ینزار هەین**"
    
    @staticmethod
    def no_negative_users():
        return "✅ **هیچ کەسەکێ ینزار نینە**"
    
    @staticmethod
    def inactive_warning(mention, points):
        return f"{mention} **24 دەمژمێرە نە ئاخڤتی** +{points} ینزار\n\n⚠️ ئەفە ناما ئاگهداریێ یە ئەگەر نامەکێ ڤرێکەیە گروپی دێ ینزارێن تە سڤر بن"
    
    @staticmethod
    def daily_top_report(top_users):
        if not top_users:
            return "📊 **هیچ نامەیەک نەهاتە** ئەڤروژێ"
        
        message = "🏆 **ئەو کەسێن ژ هەمیان پتر نامە رێکرین د روژێ دا** 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        for i, user in enumerate(top_users[:5]):
            user_id, username, first_name, msg_count = user
            if username:
                name = f"@{username}"
            else:
                name = f"<a href='tg://user?id={user_id}'>{first_name}</a>"
            message += f"{medals[i]} {name} - {msg_count} نامە\n"
        
        return message
    
    @staticmethod
    def help_message():
        return """📋 **تایبەتمەندیێن بوتی**

/test - کنترول کرنا بوتی
/r - ئەوان کەسێن ینزار هەین تاک بکە
/id, ايدي, ایدی - زانیاریێن کەسی
/24h - ئەو کەسێن 24 سعەتا نە ئاخڤتین (ادمین)
/nadmin - لیستا ادمینا جدید بکە (ادمین)
/sync - هەمی ئەندامان سنکرونیزە بکە (ادمین)

⚠️ تنێ ادمین دشێن بکار بینن: /24h, /nadmin, /sync"""
    
    @staticmethod
    def error_message(error_type="general"):
        errors = {
            "wrong_group": "🚫 ئەڤ تایبەتمەندیە تنێ د گروپی دا کار دکت",
            "not_admin": "⛔ پێدفیە ادمین بی هتا بشێی بکار بینی",
            "general": "❌ خەلەتیەک چێبی دوبارە هەولبدە",
            "no_user": "👤 ئەندام نەهاتە دیتن"
        }
        return errors.get(error_type, errors["general"])
    
    @staticmethod
    def only_group():
        return "🚫 ئەڤ بوتە تنێ د گروپێ تایبەت دا کار دکت"

translations = BadiniTranslations()

def is_allowed_group(message):
    if message.chat.type == 'private':
        return False
    return message.chat.id == ALLOWED_GROUP_ID

def is_admin(user_id, chat_id):
    try:
        admin = bot.get_chat_member(chat_id, user_id)
        return admin.status in ['administrator', 'creator']
    except:
        return False

def update_admin_cache(chat_id):
    global admin_cache
    try:
        admins = bot.get_chat_administrators(chat_id)
        admin_cache = set([admin.user.id for admin in admins])
        print(f"✅ Admin cache güncellendi: {len(admin_cache)} admin")
    except Exception as e:
        print(f"❌ Admin cache hatası: {e}")

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

def sync_all_members(chat_id):
    """Gruptaki TÜM üyeleri Telegram API ile al"""
    print("🔄 Tüm üyeler taranıyor...")
    count = 0
    users_found = set()
    
    try:
        # Önce adminleri al
        admins = bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if not user.is_bot:
                db.add_user_manual(user.id, user.username, user.first_name, user.last_name)
                users_found.add(user.id)
                count += 1
                print(f"✅ Admin eklendi: {user.first_name}")
        
        # Grubun toplam üye sayısını al
        try:
            total_members = bot.get_chat_members_count(chat_id)
            print(f"📊 Toplam üye sayısı: {total_members}")
            
            # Her üyeyi tek tek al
            offset = 0
            limit = 100
            
            while offset < total_members:
                members = bot.get_chat_members(chat_id, offset=offset, limit=limit)
                if not members:
                    break
                
                for member in members:
                    user = member.user
                    if not user.is_bot and user.id not in users_found:
                        db.add_user_manual(user.id, user.username, user.first_name, user.last_name)
                        users_found.add(user.id)
                        count += 1
                        print(f"📌 Üye eklendi: {user.first_name}")
                
                offset += limit
                
        except Exception as e:
            print(f"⚠️ Üye listesi alınırken hata: {e}")
            print("📌 Bot admin yetkisinde ve grup 50-60 kişi olmalı")
        
        print(f"✅ Toplam {count} üye eklendi")
        return count
        
    except Exception as e:
        print(f"❌ Üye tarama hatası: {e}")
        return 0

def check_inactive_users():
    print("🔍 24 saat konuşmayanlar kontrol ediliyor...")
    
    try:
        inactive_users = db.get_inactive_users_24h()
        
        for user in inactive_users:
            user_id, username, first_name, last_date, negative_points, last_notified = user
            
            if user_id == bot.get_me().id:
                continue
            
            if last_date is None:
                print(f"📌 Hiç konuşmamış: {user_id}")
                db.add_negative_point(user_id)
                new_points = db.get_user_negative_points(user_id)
            else:
                if last_notified:
                    try:
                        last_notified_time = datetime.datetime.fromisoformat(str(last_notified))
                        if datetime.datetime.now() - last_notified_time < datetime.timedelta(hours=24):
                            continue
                    except:
                        pass
                
                db.add_negative_point(user_id)
                new_points = db.get_user_negative_points(user_id)
            
            mention = get_mention_html(user_id, username, first_name)
            warning_msg = translations.inactive_warning(mention, new_points)
            
            try:
                bot.send_message(ALLOWED_GROUP_ID, warning_msg, parse_mode='HTML')
                db.update_last_notified(user_id)
                print(f"🔔 Etiketlendi: {user_id}")
            except Exception as e:
                print(f"❌ Etiketleme hatası: {e}")
                
    except Exception as e:
        print(f"❌ 24 saat kontrol hatası: {e}")

def send_daily_report():
    print("📊 Günlük rapor gönderiliyor...")
    try:
        top_users = db.get_daily_top_users(5)
        report_msg = translations.daily_top_report(top_users)
        bot.send_message(ALLOWED_GROUP_ID, report_msg, parse_mode='HTML')
        print("✅ Günlük rapor gönderildi")
    except Exception as e:
        print(f"❌ Günlük rapor hatası: {e}")

@bot.message_handler(commands=['start'])
def cmd_start(message):
    try:
        if message.chat.type == 'private':
            bot.reply_to(message, translations.only_group())
            return
        if is_allowed_group(message):
            bot.reply_to(message, "🔰 بوت داتایێن گروپی مە. بۆ هاریکاریێ چێکی /help")
    except Exception as e:
        print(f"❌ start hatası: {e}")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    try:
        if not is_allowed_group(message):
            bot.reply_to(message, translations.error_message("wrong_group"))
            return
        bot.reply_to(message, translations.help_message(), parse_mode='Markdown')
    except Exception as e:
        print(f"❌ help hatası: {e}")

@bot.message_handler(commands=['test'])
def cmd_test(message):
    try:
        if not is_allowed_group(message):
            bot.reply_to(message, translations.error_message("wrong_group"))
            return
        
        all_users = db.get_all_users()
        total_users = len(all_users)
        negative_users = db.get_users_with_negative_points()
        users_with_negatives = len(negative_users)
        last_check = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        report = translations.test_report(True, total_users, users_with_negatives, last_check, True, 0)
        bot.reply_to(message, report, parse_mode='Markdown')
    except Exception as e:
        print(f"❌ test hatası: {e}")

@bot.message_handler(commands=['r'])
def cmd_r(message):
    try:
        if not is_allowed_group(message):
            bot.reply_to(message, translations.error_message("wrong_group"))
            return
        
        negative_users = db.get_users_with_negative_points()
        if not negative_users:
            bot.reply_to(message, translations.no_negative_users(), parse_mode='Markdown')
            return
        
        msg = translations.negative_list_title() + "\n\n"
        for user in negative_users:
            user_id, username, first_name, points = user
            if username:
                msg += f"• @{username} - ینزار: {points}\n"
            else:
                name = first_name if first_name else "بێ ناف"
                msg += f"• <a href='tg://user?id={user_id}'>{name}</a> - ینزار: {points}\n"
        
        bot.reply_to(message, msg, parse_mode='HTML')
    except Exception as e:
        print(f"❌ r komutu hatası: {e}")

@bot.message_handler(commands=['24h'])
def cmd_24h(message):
    try:
        if not is_allowed_group(message):
            bot.reply_to(message, translations.error_message("wrong_group"))
            return
        if not is_admin(message.from_user.id, message.chat.id):
            bot.reply_to(message, translations.error_message("not_admin"))
            return
        
        inactive_users = db.get_inactive_users_24h()
        if not inactive_users:
            bot.reply_to(message, "📊 هەمی کەس ئاکتیڤن د 24 سعەتان دا!")
            return
        
        msg = "⏰ **ئەو کەسێن 24 سعەتا نە ئاخڤتین**\n\n"
        for user in inactive_users:
            user_id, username, first_name, last_date, points, _ = user
            mention = get_mention_html(user_id, username, first_name)
            if last_date is None:
                last_date_str = "هیچ نامەیەک نەنارد"
            else:
                last_date_str = str(last_date)[:16]
            msg += f"• {mention} - ینزار: {points} (دوایین نامە: {last_date_str})\n"
        
        bot.reply_to(message, msg, parse_mode='HTML')
    except Exception as e:
        print(f"❌ 24h komutu hatası: {e}")

@bot.message_handler(commands=['nadmin'])
def cmd_nadmin(message):
    try:
        if not is_allowed_group(message):
            bot.reply_to(message, translations.error_message("wrong_group"))
            return
        if not is_admin(message.from_user.id, message.chat.id):
            bot.reply_to(message, translations.error_message("not_admin"))
            return
        
        update_admin_cache(message.chat.id)
        bot.reply_to(message, f"👑 لیستا ادمینا هات دیتن: {len(admin_cache)} ئادمین")
    except Exception as e:
        print(f"❌ nadmin hatası: {e}")

@bot.message_handler(commands=['sync'])
def cmd_sync(message):
    try:
        if not is_allowed_group(message):
            bot.reply_to(message, translations.error_message("wrong_group"))
            return
        if not is_admin(message.from_user.id, message.chat.id):
            bot.reply_to(message, translations.error_message("not_admin"))
            return
        
        bot.reply_to(message, "🔄 سنکرونیزە کرنا ئەندامان دەست پێ کر...")
        count = sync_all_members(message.chat.id)
        bot.reply_to(message, f"✅ {count} ئەندام هاتنە زیادکرن")
        
    except Exception as e:
        print(f"❌ sync hatası: {e}")
        bot.reply_to(message, translations.error_message("general"))

@bot.message_handler(func=lambda message: message.text and message.text.lower() in ['id', 'ايدي', 'ایدی', 'ıd'])
def cmd_id(message):
    try:
        if not is_allowed_group(message):
            return
        
        user = message.from_user
        user_id = user.id
        
        db.add_user(user_id, user.username, user.first_name, user.last_name)
        stats = db.get_user_stats(user_id)
        
        if not stats:
            bot.reply_to(message, translations.error_message("no_user"))
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

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_messages(message):
    try:
        if not is_allowed_group(message):
            return
        
        if message.text and message.text.startswith('/'):
            command = message.text.split()[0].lower()
            if command in ['/test', '/r', '/24h', '/nadmin', '/help', '/start', '/sync']:
                return
        
        user = message.from_user
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        db.update_user_activity(user.id)
        
    except Exception as e:
        print(f"❌ handle_messages hatası: {e}")

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    try:
        if not is_allowed_group(message):
            return
        
        for new_member in message.new_chat_members:
            if new_member.id == bot.get_me().id:
                bot.reply_to(message, "🔰 بوت داتایێن گروپی مە. بۆ هاریکاریێ چێکی /help")
                update_admin_cache(message.chat.id)
                start_scheduler(check_inactive_users, send_daily_report, ALLOWED_GROUP_ID)
                count = sync_all_members(message.chat.id)
                bot.reply_to(message, f"✅ {count} ئەندام هاتنە زیادکرن")
                print(f"✅ Bot gruba eklendi, {count} üye tarandı!")
            else:
                db.add_user_manual(new_member.id, new_member.username, new_member.first_name, new_member.last_name)
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

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 BOT BAŞLATILIYOR...")
    print("=" * 50)
    print(f"🔑 Token: {BOT_TOKEN[:10] if BOT_TOKEN else 'YOK'}...")
    print(f"👥 Grup ID: {ALLOWED_GROUP_ID}")
    print("-" * 50)
    
    try:
        update_admin_cache(ALLOWED_GROUP_ID)
    except Exception as e:
        print(f"⚠️ Admin cache alınamadı: {e}")
    
    start_scheduler(check_inactive_users, send_daily_report, ALLOWED_GROUP_ID)
    
    print("-" * 50)
    print("✅ HAZIR KOMUTLAR:")
    print("   • /start, /help")
    print("   • /test (bot durumu)")
    print("   • /r (eksi puanı olanlar)")
    print("   • /24h (admin)")
    print("   • /nadmin (admin)")
    print("   • /sync (admin - tüm üyeleri ekle)")
    print("   • id, ايدي, ایدی, ıd (slashsiz)")
    print("-" * 50)
    print("🚀 Polling başlıyor...")
    print("=" * 50)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Polling hatası: {e}")
        time.sleep(5)
