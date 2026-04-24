import sqlite3
import os
import pandas as pd
from datetime import datetime
import numpy as np

# Veritabanı dosyası uygulamayla aynı dizinde (bist_cache.db)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS takas_data (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            foreign_ratio REAL,
            daily_change REAL,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.commit()
    return conn

def _fetch_takas_mock(ticker, date_str):
    """
    Geçici: Harici bir API (Matriks/Finnet vb.) satın alınana kadar 
    BIST hissesinin Yabancı Takas Oranını sentetik (mock) üretir.
    Rastgele ama hisseye özgü (hash tabanlı) tutarlı değerler verir.
    """
    # Basit bir deterministik hash
    seed = sum(ord(c) for c in ticker) + int(date_str.replace('-',''))
    np.random.seed(seed)
    
    # Derin tahtalarda (THYAO vb.) oran yüksek, yan tahtalarda düşük olsun
    base_ratio = (seed % 40) + 10.0 # 10 ile 50 arası
    daily_change = np.random.uniform(-1.5, 2.0)
    
    current_ratio = max(0.1, base_ratio + daily_change)
    
    return current_ratio, daily_change

def fetch_and_save_takas(ticker):
    """
    Belirtilen hissenin takas bilgisini getirir ve veritabanına kaydeder.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    conn = _get_connection()
    
    # Veritabanında bugün için kayıt var mı?
    cur = conn.execute("SELECT foreign_ratio, daily_change FROM takas_data WHERE ticker=? AND date=?", (ticker, today))
    row = cur.fetchone()
    
    if row:
        return {'foreign_ratio': row[0], 'daily_change': row[1]}
        
    # --- BURAYA GERÇEK API ENTEGRASYONU GELECEK ---
    # Şimdilik mock veri kullanıyoruz
    foreign_ratio, daily_change = _fetch_takas_mock(ticker, today)
    
    conn.execute("INSERT OR REPLACE INTO takas_data (ticker, date, foreign_ratio, daily_change) VALUES (?, ?, ?, ?)",
                 (ticker, today, foreign_ratio, daily_change))
    conn.commit()
    conn.close()
    
    return {'foreign_ratio': foreign_ratio, 'daily_change': daily_change}

def get_takas_data(ticker):
    """
    Sistemin diğer modülleri tarafından kullanılacak olan ana sorgu fonksiyonu.
    """
    return fetch_and_save_takas(ticker)
