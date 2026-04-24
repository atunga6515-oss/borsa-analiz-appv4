import pandas as pd
import requests

url = 'https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Yabanci-Oranlari.aspx'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
}

try:
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)
    if not tables:
        print("Tablo bulunamadı")
    else:
        for i, t in enumerate(tables):
            print(f"Table {i} columns: {t.columns.tolist()[:5]}")
            if 'Hisse' in t.columns or 'Sembol' in t.columns or any('Yabancı Oranı' in str(c) for c in t.columns):
                print(t.head())
except Exception as e:
    print(e)
