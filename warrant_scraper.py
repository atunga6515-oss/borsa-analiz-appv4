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
    İş Varant web sitesi üzerinden güncel varant listesini çeker. (Yenilenmiş API)
    """
    # Alternatif 1: Piyasa Verileri Endpoint
    url = "https://www.isvarant.com/api/piyasaanaliz/varantlistesi"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.isvarant.com/piyasa-verileri/varant-listesi",
        "Content-Type": "application/json"
    }

    try:
        # Önce POST deniyoruz (Birçok Next.js API'si POST bekler)
        response = requests.post(url, headers=headers, json={}, timeout=10)
        
        # Eğer POST 404 veya 405 verirse GET deneyelim
        if response.status_code != 200:
            response = requests.get("https://www.isvarant.com/api/v1/warrant/getwarrants", headers=headers, timeout=10)

        if response.status_code != 200:
            return f"Hata: İş Varant API şu an yanıt vermiyor (HTTP {response.status_code})"
        
        data = response.json()
        raw_warrants = data if isinstance(data, list) else data.get('data', [])
        
        if not raw_warrants:
            return "Varant verisi boş geldi."

        warrant_list = []
        for w in raw_warrants:
            try:
                # Key eşleşmeleri değişmiş olabilir, esnek yapı:
                ticker = w.get('Symbol') or w.get('symbol') or w.get('kod')
                underlying = w.get('UnderlyingAssetCode') or w.get('underlying')
                w_type = 'CALL' if 'Alım' in str(w.get('Type', '')) else 'PUT'
                strike = float(str(w.get('StrikePrice', 0)).replace(',', '.'))
                expiry_raw = w.get('MaturityDate') or w.get('vade')
                expiry_date = expiry_raw.split('T')[0] if expiry_raw else None
                multiplier = float(str(w.get('ConversionRatio', 1)).replace(',', '.'))
                iv = float(str(w.get('Volatility', 50)).replace(',', '.')) / 100

                if ticker and underlying:
                    warrant_list.append((
                        ticker, underlying, w_type, strike, expiry_date, multiplier, 'IS VARANT', iv
                    ))
            except: continue

        # Veritabanına kaydet
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM warrants WHERE issuer = 'IS VARANT'")
        cursor.executemany("INSERT INTO warrants (ticker, underlying, type, strike, expiry_date, multiplier, issuer, iv) VALUES (?,?,?,?,?,?,?,?)", warrant_list)
        conn.commit()
        conn.close()
        
        return f"BAŞARILI: {len(warrant_list)} İş Varant verisi güncellendi."
    except Exception as e:
        return f"IsVarant Hatası: {str(e)}"

def scrape_ak_varant():
    """
    Ak Varant web sitesi üzerinden güncel varant listesini çeker.
    """
    url = "https://www.akvarant.com/api/Price/GetWarrantList"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return f"AkVarant Hata: {response.status_code}"
            
        raw_warrants = response.json()
        warrant_list = []
        for w in raw_warrants:
            try:
                ticker = w.get('WarrantCode')
                underlying = w.get('UnderlyingCode')
                w_type = 'CALL' if w.get('OptionType') == 1 else 'PUT'
                strike = float(w.get('StrikePrice', 0))
                expiry_date = w.get('MaturityDate').split('T')[0]
                multiplier = float(w.get('ConversionRatio', 1))
                iv = float(w.get('ImpliedVolatility', 50)) / 100

                warrant_list.append((
                    ticker, underlying, w_type, strike, expiry_date, multiplier, 'AK VARANT', iv
                ))
            except: continue

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM warrants WHERE issuer = 'AK VARANT'")
        cursor.executemany("INSERT INTO warrants (ticker, underlying, type, strike, expiry_date, multiplier, issuer, iv) VALUES (?,?,?,?,?,?,?,?)", warrant_list)
        conn.commit()
        conn.close()
        return f"BAŞARILI: {len(warrant_list)} Ak Varant verisi güncellendi."
    except Exception as e:
        return f"AkVarant Hatası: {str(e)}"
