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
    Ak Varant web sitesi üzerinden güncel varant listesini çeker. (Yeni Domain: varant.akyatirim.com.tr)
    """
    # Eski www.akvarant.com yerine güncel domain:
    url = "https://varant.akyatirim.com.tr/api/Price/GetWarrantList"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://varant.akyatirim.com.tr/piyasa-analiz/varant-takip",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Eğer bu endpoint HTML dönüyorsa, muhtemelen bir yönlendirme vardır.
        if response.status_code != 200 or "text/html" in response.headers.get("Content-Type", "").lower():
            # Alternatif Endpoint Denemesi
            url_alt = "https://varant.akyatirim.com.tr/piyasa-analiz/GetVarantTakipList"
            response = requests.post(url_alt, headers=headers, json={}, timeout=10)

        if response.status_code != 200:
            return f"AkVarant Hata: {response.status_code}"
            
        try:
            raw_warrants = response.json()
        except:
            return "AkVarant Hatası: Sunucudan beklenen JSON verisi alınamadı (HTML döndü)."

        if not raw_warrants:
            return "AkVarant verisi boş geldi."

        warrant_list = []
        for w in raw_warrants:
            try:
                # Ak Yatırım API alan adları:
                ticker = w.get('WarrantCode') or w.get('Symbol')
                underlying = w.get('UnderlyingCode') or w.get('UnderlyingAssetCode')
                
                # OptionType 1: CALL, 2: PUT (Ak Yatırım standardı)
                opt_type = w.get('OptionType') or w.get('Type')
                w_type = 'CALL' if str(opt_type) in ['1', 'Alım', 'Call'] else 'PUT'
                
                strike = float(str(w.get('StrikePrice', 0)).replace(',', '.'))
                expiry_raw = w.get('MaturityDate') or w.get('Vade')
                expiry_date = expiry_raw.split('T')[0] if expiry_raw else None
                multiplier = float(str(w.get('ConversionRatio', 1)).replace(',', '.'))
                iv = float(str(w.get('ImpliedVolatility', w.get('Volatility', 50))).replace(',', '.')) / 100

                if ticker and underlying:
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

def process_warrant_excel(uploaded_file, issuer):
    """
    Kullanıcının yüklediği Excel dosyasını işler ve veritabanına kaydeder.
    """
    try:
        df = pd.read_excel(uploaded_file)
        warrant_list = []
        
        if issuer == 'IS VARANT':
            for _, row in df.iterrows():
                try:
                    ticker = str(row.get('Sembol', row.get('Varant Sembolü', ''))).strip()
                    underlying = str(row.get('Dayanak Varlık', row.get('Dayanak', ''))).strip()
                    raw_type = str(row.get('Tip', '')).upper()
                    w_type = 'CALL' if 'ALIM' in raw_type or 'CALL' in raw_type else 'PUT'
                    strike = float(row.get('Kullanım Fiyatı', row.get('Kullanım', 0)))
                    vade = row.get('Vade Tarihi', row.get('Vade', None))
                    expiry_date = None
                    if isinstance(vade, datetime):
                        expiry_date = vade.strftime('%Y-%m-%d')
                    elif isinstance(vade, str):
                        expiry_date = vade.split(' ')[0]
                    multiplier = float(row.get('Çarpan', row.get('Duyarlılık', 1)))
                    iv = float(row.get('Zımni Oynaklık', row.get('Volatility', 50)))
                    if iv > 1: iv /= 100
                    if ticker and underlying:
                        warrant_list.append((ticker, underlying, w_type, strike, expiry_date, multiplier, 'IS VARANT', iv))
                except: continue
        elif issuer == 'AK VARANT':
            for _, row in df.iterrows():
                try:
                    ticker = str(row.get('Varant Kodu', row.get('Kod', ''))).strip()
                    underlying = str(row.get('Dayanak Varlık', row.get('Dayanak', ''))).strip()
                    raw_type = str(row.get('Tip', '')).upper()
                    w_type = 'CALL' if 'ALIM' in raw_type or 'CALL' in raw_type else 'PUT'
                    strike = float(row.get('Kullanım Fiyatı', row.get('Strike', 0)))
                    vade = row.get('Vade Tarihi', row.get('Vade', None))
                    expiry_date = None
                    if isinstance(vade, datetime):
                        expiry_date = vade.strftime('%Y-%m-%d')
                    multiplier = float(row.get('Çarpan', 1))
                    iv = float(row.get('Zımni Oynaklık', row.get('Oynaklık', 50)))
                    if iv > 1: iv /= 100
                    if ticker and underlying:
                        warrant_list.append((ticker, underlying, w_type, strike, expiry_date, multiplier, 'AK VARANT', iv))
                except: continue
        if not warrant_list: return "Hata: Excel formatı tanınamadı."
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute(f"DELETE FROM warrants WHERE issuer = '{issuer}'")
        cursor.executemany("INSERT INTO warrants (ticker, underlying, type, strike, expiry_date, multiplier, issuer, iv) VALUES (?,?,?,?,?,?,?,?)", warrant_list)
        conn.commit(); conn.close()
        return f"BAŞARILI: {len(warrant_list)} varant yüklendi."
    except Exception as e: return f"Excel Hatası: {str(e)}"
