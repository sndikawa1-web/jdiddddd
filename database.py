# database.py - Veritabanı işlemleri

import sqlite3
import psycopg2
import datetime
import os
from config import DATABASE_URL

class Database:
    def __init__(self):
        self.is_postgres = DATABASE_URL and "postgres" in DATABASE_URL
        
        if self.is_postgres:
            print("✅ PostgreSQL kullanılıyor (veriler kalıcı)")
            self.conn = psycopg2.connect(DATABASE_URL)
            self.cursor = self.conn.cursor()
        else:
            print("⚠️ SQLite kullanılıyor (veriler geçici)")
            self.conn = sqlite3.connect("bot_database.db", check_same_thread=False)
            self.cursor = self.conn.cursor()
        
        self._create_tables()
    
    def _create_tables(self):
        if self.is_postgres:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    last_message_date TIMESTAMP,
                    negative_points INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_notified_24h TIMESTAMP
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    date DATE,
                    message_count INTEGER DEFAULT 0,
                    UNIQUE(user_id, date)
                )
            """)
        else:
            self.cursor.execute("""
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
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date DATE,
                    message_count INTEGER DEFAULT 0,
                    UNIQUE(user_id, date)
                )
            """)
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name=None):
        """Yeni kullanıcı ekle - last_message_date NULL olarak eklenir"""
        try:
            if self.is_postgres:
                self.cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, last_message_date)
                    VALUES (%s, %s, %s, %s, NULL)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name
                """, (user_id, username, first_name, last_name))
            else:
                self.cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, last_message_date)
                    VALUES (?, ?, ?, ?, NULL)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name,
                        last_name = excluded.last_name
                """, (user_id, username, first_name, last_name))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Hata: {e}")
            return False
    
    def remove_user(self, user_id):
        try:
            if self.is_postgres:
                self.cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                self.cursor.execute("DELETE FROM daily_stats WHERE user_id = %s", (user_id,))
            else:
                self.cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                self.cursor.execute("DELETE FROM daily_stats WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Hata: {e}")
            return False
    
    def update_user_activity(self, user_id):
        """Kullanıcı mesaj gönderdiğinde güncelle - eksiler sıfırlanır"""
        try:
            now = datetime.datetime.now()
            if self.is_postgres:
                self.cursor.execute("""
                    UPDATE users 
                    SET last_message_date = %s, 
                        total_messages = total_messages + 1, 
                        negative_points = 0
                    WHERE user_id = %s
                """, (now, user_id))
            else:
                self.cursor.execute("""
                    UPDATE users 
                    SET last_message_date = ?, 
                        total_messages = total_messages + 1, 
                        negative_points = 0
                    WHERE user_id = ?
                """, (now, user_id))
            
            today = now.date()
            if self.is_postgres:
                self.cursor.execute("""
                    INSERT INTO daily_stats (user_id, date, message_count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT(user_id, date) DO UPDATE SET
                        message_count = daily_stats.message_count + 1
                """, (user_id, today))
            else:
                self.cursor.execute("""
                    INSERT INTO daily_stats (user_id, date, message_count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, date) DO UPDATE SET
                        message_count = message_count + 1
                """, (user_id, today))
            
            self.conn.commit()
            
            if self.is_postgres:
                self.cursor.execute("SELECT negative_points FROM users WHERE user_id = %s", (user_id,))
            else:
                self.cursor.execute("SELECT negative_points FROM users WHERE user_id = ?", (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"Hata: {e}")
            return 0
    
    def add_negative_point(self, user_id):
        try:
            if self.is_postgres:
                self.cursor.execute("UPDATE users SET negative_points = negative_points + 1 WHERE user_id = %s", (user_id,))
            else:
                self.cursor.execute("UPDATE users SET negative_points = negative_points + 1 WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Hata: {e}")
            return False
    
    def get_user_negative_points(self, user_id):
        if self.is_postgres:
            self.cursor.execute("SELECT negative_points FROM users WHERE user_id = %s", (user_id,))
        else:
            self.cursor.execute("SELECT negative_points FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def get_users_with_negative_points(self):
        if self.is_postgres:
            self.cursor.execute("SELECT user_id, username, first_name, negative_points FROM users WHERE negative_points > 0 ORDER BY negative_points DESC")
        else:
            self.cursor.execute("SELECT user_id, username, first_name, negative_points FROM users WHERE negative_points > 0 ORDER BY negative_points DESC")
        return self.cursor.fetchall()
    
    def get_inactive_users_24h(self):
        """24 saat mesaj göndermeyen veya hiç mesaj göndermemiş kullanıcıları bul"""
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=24)
        if self.is_postgres:
            self.cursor.execute("""
                SELECT user_id, username, first_name, last_message_date, negative_points, last_notified_24h
                FROM users 
                WHERE last_message_date IS NULL 
                   OR last_message_date < %s
            """, (cutoff,))
        else:
            self.cursor.execute("""
                SELECT user_id, username, first_name, last_message_date, negative_points, last_notified_24h
                FROM users 
                WHERE last_message_date IS NULL 
                   OR last_message_date < ?
            """, (cutoff,))
        return self.cursor.fetchall()
    
    def update_last_notified(self, user_id):
        try:
            now = datetime.datetime.now()
            if self.is_postgres:
                self.cursor.execute("UPDATE users SET last_notified_24h = %s WHERE user_id = %s", (now, user_id))
            else:
                self.cursor.execute("UPDATE users SET last_notified_24h = ? WHERE user_id = ?", (now, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Hata: {e}")
            return False
    
    def get_daily_top_users(self, limit=5):
        today = datetime.datetime.now().date()
        if self.is_postgres:
            self.cursor.execute("""
                SELECT ds.user_id, u.username, u.first_name, ds.message_count
                FROM daily_stats ds JOIN users u ON ds.user_id = u.user_id
                WHERE ds.date = %s ORDER BY ds.message_count DESC LIMIT %s
            """, (today, limit))
        else:
            self.cursor.execute("""
                SELECT ds.user_id, u.username, u.first_name, ds.message_count
                FROM daily_stats ds JOIN users u ON ds.user_id = u.user_id
                WHERE ds.date = ? ORDER BY ds.message_count DESC LIMIT ?
            """, (today, limit))
        return self.cursor.fetchall()
    
    def get_all_users(self):
        if self.is_postgres:
            self.cursor.execute("SELECT user_id, username, first_name FROM users")
        else:
            self.cursor.execute("SELECT user_id, username, first_name FROM users")
        return self.cursor.fetchall()
    
    def get_user_stats(self, user_id):
        if self.is_postgres:
            self.cursor.execute("""
                SELECT username, first_name, total_messages, negative_points, last_message_date, joined_date
                FROM users WHERE user_id = %s
            """, (user_id,))
        else:
            self.cursor.execute("""
                SELECT username, first_name, total_messages, negative_points, last_message_date, joined_date
                FROM users WHERE user_id = ?
            """, (user_id,))
        return self.cursor.fetchone()
    
    def add_user_manual(self, user_id, username, first_name, last_name=None):
        """Manuel olarak kullanıcı ekle - hiç mesaj göndermemiş olarak"""
        try:
            if self.is_postgres:
                self.cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, last_message_date, total_messages)
                    VALUES (%s, %s, %s, %s, NULL, 0)
                    ON CONFLICT(user_id) DO NOTHING
                """, (user_id, username, first_name, last_name))
            else:
                self.cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, last_message_date, total_messages)
                    VALUES (?, ?, ?, ?, NULL, 0)
                    ON CONFLICT(user_id) DO NOTHING
                """, (user_id, username, first_name, last_name))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Manuel ekleme hatasi: {e}")
            return False
    
    def close(self):
        self.conn.close()
