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
    Akıllı sütun eşleme ile farklı formatlardaki dosyaları da tanır.
    İş Varant formatı: ilk 3 satır başlık/tarih, 4. satır sütun isimleri.
    """
    try:
        # Önce normal oku
        df = pd.read_excel(uploaded_file, header=0)
        cols = [str(c).strip() for c in df.columns.tolist()]
        
        # Eğer ilk sütun "ENDEKS", "HİSSE" vb. ise başlık satırları var demektir
        # Gerçek başlıkları bulmak için satırları tara
        header_row = 0
        for i, row_vals in df.iterrows():
            row_str = [str(v).strip() for v in row_vals.values]
            if any('Sembol' in s or 'Varant' in s for s in row_str):
                header_row = i + 1  # +1 çünkü header=0 ile okuduk
                break
        
        if header_row > 0:
            uploaded_file.seek(0)  # Dosyayı başa sar
            df = pd.read_excel(uploaded_file, header=header_row)
        
        cols = [str(c).strip() for c in df.columns.tolist()]
        df.columns = cols
        
        # Akıllı Sütun Eşleme: Sütun isimlerinde anahtar kelime ara
        def find_col(keywords, default=None):
            for kw in keywords:
                for c in cols:
                    if kw.lower() in c.lower():
                        return c
            return default

        col_ticker = find_col(['Sembol', 'Varant Kodu', 'Kod', 'Symbol'])
        col_underlying = find_col(['D.Varl', 'Dayanak', 'Underlying'])
        col_type = find_col(['Tip', 'Type', 'Tur'])
        col_strike = find_col(['Kul.F', 'Kullan', 'Strike'])
        col_expiry = find_col(['Vade', 'Maturity', 'Son'])
        col_multiplier = find_col(['Carpan', 'Çarpan', 'Duyarl', 'Ratio', 'Conversion'])
        col_iv = find_col(['Oynakl', 'Volatil', 'IV', 'Zimni'])

        if not col_ticker or not col_underlying:
            return f"Hata: Sütunlar tanınamadı. Dosyadaki sütunlar: {cols}"

        warrant_list = []
        for _, row in df.iterrows():
            try:
                ticker = str(row[col_ticker]).strip()
                underlying = str(row[col_underlying]).strip()
                
                if not ticker or ticker == 'nan' or not underlying or underlying == 'nan':
                    continue

                w_type = 'PUT'
                if col_type:
                    raw_type = str(row[col_type]).upper()
                    if 'ALIM' in raw_type or 'CALL' in raw_type or 'A' == raw_type.strip():
                        w_type = 'CALL'

                strike = 0.0
                if col_strike:
                    try: strike = float(str(row[col_strike]).replace(',', '.'))
                    except: strike = 0.0

                expiry_date = None
                if col_expiry:
                    vade = row[col_expiry]
                    if isinstance(vade, datetime):
                        expiry_date = vade.strftime('%Y-%m-%d')
                    elif isinstance(vade, str) and vade != 'nan':
                        expiry_date = vade.split(' ')[0].split('T')[0]

                multiplier = 1.0
                if col_multiplier:
                    try: multiplier = float(str(row[col_multiplier]).replace(',', '.'))
                    except: multiplier = 1.0

                iv = 0.40
                if col_iv:
                    try:
                        iv = float(str(row[col_iv]).replace(',', '.').replace('%', ''))
                        if iv > 1: iv /= 100
                    except: iv = 0.40

                warrant_list.append((ticker, underlying, w_type, strike, expiry_date, multiplier, issuer, iv))
            except: continue

        if not warrant_list:
            return f"Hata: Veri okunamadı. Sütunlar: {cols}"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM warrants WHERE issuer = ?", (issuer,))
        cursor.executemany("INSERT INTO warrants (ticker, underlying, type, strike, expiry_date, multiplier, issuer, iv) VALUES (?,?,?,?,?,?,?,?)", warrant_list)
        conn.commit()
        conn.close()
        return f"BAŞARILI: {len(warrant_list)} varant yüklendi. (Eşlenen sütunlar: Sembol={col_ticker}, Dayanak={col_underlying})"
    except Exception as e:
        return f"Excel Hatası: {str(e)}"
