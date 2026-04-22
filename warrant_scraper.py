import requests
import pandas as pd
import sqlite3
import os
from datetime import datetime
import time

# Varant Scraper - Gerçek Veri Kaynağı Entegrasyonu

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def scrape_is_varant():
    """
    İş Varant web sitesi üzerinden tüm güncel varant listesini çeker.
    Gereksinim: requests, pandas
    """
    url = "https://www.isvarant.com/api/v1/warrant/getwarrants"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.isvarant.com/piyasa-verileri/varant-listesi"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"Hata: HTTP {response.status_code}"
        
        data = response.json()
        raw_warrants = data.get('data', [])
        
        if not raw_warrants:
            return "Varant verisi bulunamadı."

        warrant_list = []
        for w in raw_warrants:
            # Temizleme ve Dönüştürme
            ticker = w.get('Symbol')
            underlying = w.get('UnderlyingAssetCode')
            w_type = 'CALL' if w.get('Type') == 'Alım' else 'PUT'
            strike = float(str(w.get('StrikePrice')).replace(',', '.'))
            
            # Tarih formatı dönüşümü
            expiry_raw = w.get('MaturityDate') # Örn: "2024-03-29T00:00:00"
            expiry_date = expiry_raw.split('T')[0] if expiry_raw else None
            
            multiplier = float(str(w.get('ConversionRatio')).replace(',', '.'))
            
            # Zımni Oynaklık (IV) - En önemli veri
            iv = float(str(w.get('Volatility')).replace(',', '.')) / 100 if w.get('Volatility') else 0.50

            warrant_list.append((
                ticker, underlying, w_type, strike, expiry_date, multiplier, 'IS VARANT', iv
            ))

        # Veritabanına kaydet (UPSERT)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Önce mevcut ihraççı verilerini temizleyelim (tazelik için)
        cursor.execute("DELETE FROM warrants WHERE issuer = 'IS VARANT'")
        
        cursor.executemany("""
            INSERT INTO warrants (ticker, underlying, type, strike, expiry_date, multiplier, issuer, iv)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, warrant_list)
        
        total_count = len(warrant_list)
        conn.commit()
        conn.close()
        
        return f"BAŞARILI: {total_count} gerçek varant verisi İş Varant'tan çekildi ve güncellendi."

    except Exception as e:
        return f"Scraping Hatası: {str(e)}"

# Opsiyonel: Ak Varant için de benzer bir yapı kurulabilir.
