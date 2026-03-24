# config.py - Bot ayarlari (DÜZELTİLMİŞ)

import os

# Railway'den alinacak degerler
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROUP_ID = os.environ.get("GROUP_ID")

# Grup ID'yi integer'a cevir
if GROUP_ID:
    ALLOWED_GROUP_ID = int(GROUP_ID)
else:
    ALLOWED_GROUP_ID = 0

# Zaman ayari
IRAQ_TIMEZONE = "Asia/Baghdad"

# Veritabani
DATABASE_URL = os.environ.get("DATABASE_URL")

print(f"Config yuklendi - Grup ID: {ALLOWED_GROUP_ID}")
