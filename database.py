# database.py - Veritabanı işlemleri
# Bu dosya tüm verileri kaydeder ve okur

import sqlite3
import datetime
import os
from config import DATABASE_URL

class Database:
    def __init__(self):
        # SQLite ile bağlantı kur (Railway'de PostgreSQL de kullanılabilir)
        if DATABASE_URL.startswith("sqlite"):
            self.conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""), check_same_thread=False)
        else:
            # PostgreSQL için (Railway'de otomatik)
            import psycopg2
            self.conn = psycopg2.connect(DATABASE_URL)
        
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Veritabanı tablolarını oluştur"""
        
        # Kullanıcılar tablosu
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                last_message_date TIMESTAMP,
                negative_points INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_notified_24h TIMESTAMP
            )
        ''')
        
        # Günlük mesaj istatistikleri tablosu
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE,
                message_count INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name=None):
        """Yeni kullanıcı ekle veya güncelle"""
        try:
            self.cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, last_message_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name
            ''', (user_id, username, first_name, last_name, datetime.datetime.now()))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Kullanıcı eklenirken hata: {e}")
            return False
    
    def remove_user(self, user_id):
        """Kullanıcıyı veritabanından sil (gruptan ayrıldığında)"""
        try:
            self.cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            self.cursor.execute("DELETE FROM daily_stats WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Kullanıcı silinirken hata: {e}")
            return False
    
    def update_user_activity(self, user_id):
        """Kullanıcı mesaj gönderdiğinde güncelle"""
        try:
            now = datetime.datetime.now()
            
            # Son mesaj zamanını ve mesaj sayısını güncelle
            self.cursor.execute('''
                UPDATE users 
                SET last_message_date = ?,
                    total_messages = total_messages + 1,
                    negative_points = 0  # Mesaj atınca eksiler sıfırlanır
                WHERE user_id = ?
            ''', (now, user_id))
            
            # Günlük istatistikleri güncelle
            today = now.date()
            self.cursor.execute('''
                INSERT INTO daily_stats (user_id, date, message_count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, date) DO UPDATE SET
                    message_count = message_count + 1
            ''', (user_id, today))
            
            self.conn.commit()
            
            # Yeni eksi puanını al
            self.cursor.execute("SELECT negative_points FROM users WHERE user_id = ?", (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            print(f"❌ Aktivite güncellenirken hata: {e}")
            return 0
    
    def add_negative_point(self, user_id):
        """Kullanıcıya 1 eksi puan ekle"""
        try:
            self.cursor.execute('''
                UPDATE users 
                SET negative_points = negative_points + 1
                WHERE user_id = ?
            ''', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Eksi eklenirken hata: {e}")
            return False
    
    def get_user_negative_points(self, user_id):
        """Kullanıcının eksi puanını al"""
        self.cursor.execute("SELECT negative_points FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def get_users_with_negative_points(self):
        """Eksi puanı olan tüm kullanıcıları listele"""
        self.cursor.execute('''
            SELECT user_id, username, first_name, negative_points 
            FROM users 
            WHERE negative_points > 0
            ORDER BY negative_points DESC
        ''')
        return self.cursor.fetchall()
    
    def get_inactive_users_24h(self):
        """24 saat mesaj göndermeyen kullanıcıları bul"""
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=24)
        self.cursor.execute('''
            SELECT user_id, username, first_name, last_message_date, negative_points, last_notified_24h
            FROM users 
            WHERE last_message_date < ? AND user_id != ?  # Bot kendini etiketlemesin
        ''', (cutoff,))
        return self.cursor.fetchall()
    
    def update_last_notified(self, user_id):
        """Son etiketlenme zamanını güncelle (aynı anda tekrar etiketlenmemesi için)"""
        try:
            now = datetime.datetime.now()
            self.cursor.execute('''
                UPDATE users 
                SET last_notified_24h = ?
                WHERE user_id = ?
            ''', (now, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Etiket zamanı güncellenirken hata: {e}")
            return False
    
    def get_daily_top_users(self, limit=5):
        """Günün en çok mesaj gönderen kullanıcılarını al"""
        today = datetime.datetime.now().date()
        self.cursor.execute('''
            SELECT ds.user_id, u.username, u.first_name, ds.message_count
            FROM daily_stats ds
            JOIN users u ON ds.user_id = u.user_id
            WHERE ds.date = ?
            ORDER BY ds.message_count DESC
            LIMIT ?
        ''', (today, limit))
        return self.cursor.fetchall()
    
    def get_all_users(self):
        """Tüm kullanıcıları al"""
        self.cursor.execute("SELECT user_id, username, first_name FROM users")
        return self.cursor.fetchall()
    
    def get_user_stats(self, user_id):
        """Kullanıcının tüm istatistiklerini al"""
        self.cursor.execute('''
            SELECT username, first_name, total_messages, negative_points, last_message_date, joined_date
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_user_info(self, user_id):
        """Kullanıcının temel bilgilerini al (id komutu için)"""
        self.cursor.execute('''
            SELECT username, first_name, last_name, total_messages, joined_date
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def close(self):
        """Veritabanı bağlantısını kapat"""
        self.conn.close()
