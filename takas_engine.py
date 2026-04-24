import requests
from bs4 import BeautifulSoup
import re
import os
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
from io import StringIO

TR_TZ = pytz.timezone("Europe/Istanbul")

# Veritabanı dosyası uygulamayla aynı dizinde (bist_cache.db)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

class TakasScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_all(self):
        """Mynet Finans Yabanci Takas Paylari sayfasından verileri çeker."""
        url = "https://finans.mynet.com/borsa/hisseler/yabanci-takas-paylari/"
        try:
            response = requests.get(url, headers=self.headers, timeout=20)
            if response.status_code != 200: return {}
            
            tables = pd.read_html(StringIO(response.text), decimal=',', thousands='.')
            if not tables: return {}
            
            df = tables[0]
            results = {}
            
            for _, row in df.iterrows():
                try:
                    # Mynet formatı: Hisse | Yabancı Payı | ...
                    raw_ticker = str(row.iloc[0]).strip()
                    if not raw_ticker or raw_ticker == "nan": continue
                    
                    ticker = raw_ticker.split()[0].upper()
                    ticker = re.sub(r'[^A-Z0-9]', '', ticker)
                    if not ticker or len(ticker) < 3: continue

                    # Yabancı oranını bul (genelde 2. veya 3. sütun)
                    ratio = 0.0
                    # DataFrame içindeki sayısal değerleri tara
                    for ci in range(1, len(row)):
                        try:
                            s_val = str(row.iloc[ci]).replace("%", "").replace(",", ".").replace(".", "").strip()
                            # Binlik ayracı temizlendiği için tekrar virgül kontrolü
                            s_val = str(row.iloc[ci]).replace("%", "").replace(",", ".").strip()
                            f_val = float(s_val)
                            if 0.0 <= f_val <= 100.0:
                                ratio = f_val
                                break
                        except: continue
                    
                    results[ticker] = ratio
                except: continue
            
            return results
        except Exception:
            return {}

def _get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
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

def update_all_takas():
    today = datetime.now(TR_TZ).strftime('%Y-%m-%d')
    conn = _get_connection()
    try:
        # Bugünün verisi zaten var mı?
        cur = conn.execute("SELECT COUNT(*) FROM takas_data WHERE date=?", (today,))
        if cur.fetchone()[0] > 100:
            return True
            
        scraper = TakasScraper()
        data = scraper.fetch_all()
        
        if not data:
            return False
            
        for ticker, ratio in data.items():
            # Günlük değişimi hesapla (Önceki en son veriyi bul)
            cur = conn.execute("SELECT foreign_ratio FROM takas_data WHERE ticker=? AND date < ? ORDER BY date DESC LIMIT 1", (ticker, today))
            prev_row = cur.fetchone()
            daily_change = 0.0
            if prev_row:
                daily_change = round(ratio - prev_row[0], 3)

            conn.execute("INSERT OR REPLACE INTO takas_data (ticker, date, foreign_ratio, daily_change) VALUES (?, ?, ?, ?)",
                        (ticker, today, ratio, daily_change))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_takas_data(ticker):
    today = datetime.now(TR_TZ).strftime('%Y-%m-%d')
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT foreign_ratio, daily_change FROM takas_data WHERE ticker=? AND date=?", (ticker, today))
        row = cur.fetchone()
        if row:
            return {'foreign_ratio': row[0], 'daily_change': row[1]}
        
        # Veri yoksa bir kereye mahsus güncellemeyi dene (thread safe olması için update içinde kontrol var)
        conn.close()
        update_all_takas()
        
        conn = _get_connection()
        cur = conn.execute("SELECT foreign_ratio, daily_change FROM takas_data WHERE ticker=? AND date=?", (ticker, today))
        row = cur.fetchone()
        if row:
            return {'foreign_ratio': row[0], 'daily_change': row[1]}
            
        return {'foreign_ratio': 0.0, 'daily_change': 0.0}
    except:
        return {'foreign_ratio': 0.0, 'daily_change': 0.0}
    finally:
        try: conn.close()
        except: pass
