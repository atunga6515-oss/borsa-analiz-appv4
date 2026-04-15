import streamlit as st
import pandas as pd
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Mevcut kütüphanelerden destek çekimleri
from kap_news import _get_client
from data_loader import fetch_data
from screener import BIST_ALL_SYMBOLS

# HTML taglerini temizleme
def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_investing_rss():
    """Investing.com Türkiye borsa hisse haberlerini RSS'den çeker."""
    url = "https://tr.investing.com/rss/news_285.rss"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        xml_data = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(xml_data)
        
        items = []
        for item in root.findall('./channel/item'):
            title = item.find('title').text if item.find('title') is not None else ""
            desc = item.find('description').text if item.find('description') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            items.append({
                "title": clean_html(title),
                "description": clean_html(desc),
                "date": pub_date
            })
        return items
    except Exception as e:
        return []

def extract_bist_tickers_from_news(news_items):
    """Metin içindeki BIST sembollerini eşleştirerek haberleri hisselere bağlar."""
    ticker_news = {sym: [] for sym in BIST_ALL_SYMBOLS}
    
    for item in news_items:
        text = (item['title'] + " " + item['description']).upper()
        # Metindeki büyük harf ve 4-5 karakterli şirket kodlarını bulma
        words = set(re.findall(r'\b[A-Z0-9]{4,5}\b', text))
        
        for sym in BIST_ALL_SYMBOLS:
            if sym in words:
                ticker_news[sym].append(item)
                
    # Sadece haberi olan hisseleri döndür
    return {k: v for k, v in ticker_news.items() if v}

def pre_filter_ticker(ticker, news_items):
    """
    Haber atılan hissenin son 15 gündeki piyasa momentumu ve hacim sinyallerini tarar.
    Amacı: Her hisse için API kotası yakmamak. Yalnızca fiyata yansıyan/hacim giren haberleri analiz etmek.
    """
    df = fetch_data(ticker, "1d", "1mo")
    if df.empty or len(df) < 15:
        return {"eligible": False}
    
    last_15 = df.tail(15)
    start_close = last_15.iloc[0]['Close']
    end_close = last_15.iloc[-1]['Close']
    
    px_chg = ((end_close - start_close) / start_close) * 100
    
    # Hacim artış kontrolü (Son 3 gün ortalaması vs Önceki 12 gün ortalaması)
    avg_vol_recent = last_15.tail(3)['Volume'].mean()
    avg_vol_past = last_15.head(12)['Volume'].mean()
    vol_chg = 0
    if avg_vol_past > 0:
        vol_chg = ((avg_vol_recent - avg_vol_past) / avg_vol_past) * 100
        
    # Eğer haber varsa, ufak bir tepki bile yeterlidir. Filtreyi çok sıkı tutmuyoruz.
    is_eligible = (px_chg > 1.0) or (vol_chg > 15.0) or (px_chg < -3.0) # Sürpriz şelale haberlerini de yakala
    
    return {
        "eligible": is_eligible,
        "px_chg": px_chg,
        "vol_chg": vol_chg
    }

@st.cache_data(ttl=3600*24, show_spinner=False)
def analyze_alpha_news(ticker, news_items, px_chg):
    """Gemini AI ile Alpha keşfi için güçlü prompt analizi (Yeni SDK)"""
    client = _get_client()
    if not client:
        return None
        
    news_text = "\n".join([f"- {item['title']} : {item['description'][:100]}..." for item in news_items])
    
    prompt = f"""
    Sen kıdemli bir BIST Quant Analisti ve Alpha Fırsat Avcısı Fon Yöneticisisin. 
    "{ticker}" hissesi son 15 günde tam %{px_chg:.1f} fiyat hareketi yaptı.
    Aşağıda bu hisseyle ilgili ulusal basında (Investing RSS) çıkan son haber akışları yer alıyor:

    {news_text}

    Haberleri derleyip JSON formatında analiz et. (nitelik, vade, skor 0-100, tahmin Evet/Hayır, ozet)
    SADECE JSON döndür.
    """
    
    try:
        # Yeni SDK - Batch Model Denemeleri
        response = None
        for model_name in ['gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text: break
            except: continue
            
        if not response or not response.text: return None
        
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception:
        return None

def run_alpha_discovery_pipeline(progress_bar=None):
    """Tüm motoru tek elden yönetir ve dataframe döner."""
    # 1. RSS Çekimi
    raw_news = fetch_investing_rss()
    if not raw_news:
        st.error("Investing haber havuzuna ulaşılamadı. Sunucu bağlantınızı kontrol edin.")
        return pd.DataFrame()
        
    # 2. Hisselere Göre Grupla
    ticker_groups = extract_bist_tickers_from_news(raw_news)
    
    if not ticker_groups:
        st.info("Son 24 saate ait BIST hisselerinde direkt bir şirket haberi/kod eşleşmesi bulunamadı.")
        return pd.DataFrame()

    results = []
    total = len(ticker_groups)
    
    # 3. Paralel Filtreleme & AI Analizi
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(pre_filter_ticker, t, n): (t, n) for t, n in ticker_groups.items()}
        
        for i, future in enumerate(as_completed(future_map)):
            ticker, news = future_map[future]
            try:
                flt = future.result()
                if flt["eligible"]:
                    # AI Modeline Sok
                    ai_res = analyze_alpha_news(ticker, news, flt["px_chg"])
                    if ai_res:
                        results.append({
                            "Sembol": ticker,
                            "Son 15G Kâr (%)": round(flt["px_chg"], 2),
                            "Haber Niteliği": ai_res.get("nitelik", "-"),
                            "Önem Skoru": ai_res.get("skor", 0),
                            "AI Tahmini": ai_res.get("tahmin", "-"),
                            "Öngörülen Vade": ai_res.get("vade", "-"),
                            "Haber Özeti (Alpha Filitresi)": ai_res.get("ozet", "-")
                        })
            except Exception:
                pass
                
            if progress_bar:
                p = int(((i + 1) / total) * 100)
                progress_bar.progress(min(p, 100), text=f"🤖 Alpha Avcısı Devrede... (%{min(p, 100)}) - Taranan: {ticker}")

    if results:
        # Puan yüksekten düşüğe sırala
        df = pd.DataFrame(results).sort_values(by="Önem Skoru", ascending=False).reset_index(drop=True)
        return df
    
    return pd.DataFrame()
