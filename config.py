# config.py - Bot ayarları
# Bu dosyada botun tüm ayarları bulunur

import os

# ============================================
# TELEGRAM BOT TOKENİ (Railway'den alınacak)
# ============================================
# Railway'de VARIABLES kısmına BOT_TOKEN ekleyeceksin
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ============================================
# GRUP ID (Railway'den alınacak)
# ============================================
# Railway'de VARIABLES kısmına GROUP_ID ekleyeceksin
ALLOWED_GROUP_ID = int(os.environ.get("GROUP_ID", 0))

# ============================================
# ZAMAN AYARLARI
# ============================================
IRAQ_TIMEZONE = "Asia/Baghdad"  # Irak saati

# ============================================
# RAILWAY'DE VERİTABANI BAĞLANTISI
# ============================================
# Railway otomatik olarak DATABASE_URL değişkenini ekler
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///bot_database.db")
