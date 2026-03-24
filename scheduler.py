# scheduler.py - Zamanlayıcı
# Bu dosya botun her saat başı ve her gün belirli saatte çalışmasını sağlar

import schedule
import time
import threading
import datetime
import pytz
from config import IRAQ_TIMEZONE

def get_iraq_time():
    """Irak saatini al"""
    tz = pytz.timezone(IRAQ_TIMEZONE)
    return datetime.datetime.now(tz)

def run_scheduler(check_func, report_func, group_id):
    """Zamanlayıcıyı çalıştır"""
    
    # Her saat başı 24 saat kontrolü yap
    schedule.every().hour.at(":00").do(check_func)
    
    # Her gün Irak saati 12:00'de rapor gönder
    def daily_report_with_time():
        now = get_iraq_time()
        if now.hour == 12 and now.minute == 0:
            report_func()
    
    # Her dakika kontrol et (12:00'yi yakalamak için)
    schedule.every(1).minutes.do(daily_report_with_time)
    
    print(f"⏰ Zamanlayıcı başlatıldı - Irak saati: {get_iraq_time().strftime('%Y-%m-%d %H:%M')}")
    print("   • Her saat başı: 24 saat konuşmayanları kontrol")
    print("   • Her gün 12:00: En aktif 5 kişi raporu")
    
    while True:
        schedule.run_pending()
        time.sleep(30)

def start_scheduler(check_func, report_func, group_id):
    """Zamanlayıcıyı ayrı bir thread'de başlat"""
    scheduler_thread = threading.Thread(
        target=run_scheduler,
        args=(check_func, report_func, group_id),
        daemon=True
    )
    scheduler_thread.start()
