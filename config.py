# config.py - Bot ayarları
# Bu dosyada botun tüm ayarları bulunur

import os

# ============================================
# TELEGRAM BOT TOKENİ (BURAYI DEĞİŞTİR!)
# ============================================
# @BotFather'dan aldığın token'ı aşağıya yapıştır
BOT_TOKEN = "7234567890:AAGkLx8Fm7xY9ZqW2rT3yU4i"  # <-- BUNU DEĞİŞTİR!

# ============================================
# GRUP ID (BURAYI DEĞİŞTİR!)
# ============================================
# Botun çalışacağı grubun ID'sini yaz
ALLOWED_GROUP_ID = -1001234567890  # <-- BUNU DEĞİŞTİR!

# ============================================
# ZAMAN AYARLARI
# ============================================
IRAQ_TIMEZONE = "Asia/Baghdad"  # Irak saati

# ============================================
# RAILWAY'DE VERİTABANI BAĞLANTISI
# ============================================
# Railway otomatik olarak DATABASE_URL değişkenini ekler
# Aşağıdaki satırı değiştirme!
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///bot_database.db")
