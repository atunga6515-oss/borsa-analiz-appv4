import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from data_loader import fetch_data, get_live_price
from indicators import calculate_indicators, generate_signals_and_score
from patterns import detect_candlestick_patterns
from support_resistance import calculate_best_zones
from screener import get_sector, BIST30_SYMBOLS, BIST100_SYMBOLS


# ============================================================
# HABER DUYGU ANALİZİ (Kelime Bazlı Sentiment)
# ============================================================

POZITIF_KELIMELER = [
    'arttı', 'yüksel', 'kazanç', 'kar ', 'kâr', 'büyü', 'yatırım',
    'anlaşma', 'temettü', 'olumlu', 'rekor', 'satın', 'ihale',
    'pozitif', 'uçtu', 'artış', 'güçlü', 'başarı', 'ralli', 'hedef',
    'beklenti', 'talep', 'ihracat', 'kapasite', 'sipariş'
]

NEGATIF_KELIMELER = [
    'düştü', 'zarar', 'azaldı', 'küçülme', 'kriz', 'ceza', 'dava',
    'iptal', 'olumsuz', 'düşüş', 'negatif', 'uyarı', 'risk',
    'çakıldı', 'kayıp', 'geriledi', 'sert', 'endişe', 'borç',
    'iflas', 'soruşturma', 'daraldı'
]


def _fetch_news_sentiment(ticker_base: str) -> dict:
    """Google News RSS üzerinden hisse haberlerini çekip duygu skoru hesaplar."""
    try:
        query = urllib.parse.quote(f"{ticker_base} hisse borsa")
        url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=8)
        xml_data = resp.read()
        root = ET.fromstring(xml_data)

        pos_count = 0
        neg_count = 0
        headlines = []

        for item in root.findall('./channel/item')[:10]:
            title = item.find('title').text
            headlines.append(title)
            title_lower = title.lower()
            p = sum(1 for w in POZITIF_KELIMELER if w in title_lower)
            n = sum(1 for w in NEGATIF_KELIMELER if w in title_lower)
            pos_count += p
            neg_count += n

        total = pos_count + neg_count
        if total == 0:
            sentiment_score = 50  # Nötr
        else:
            sentiment_score = (pos_count / total) * 100  # 0-100 arası

        return {
            "sentiment_score": round(sentiment_score, 1),
            "pos_count": pos_count,
            "neg_count": neg_count,
            "headline_count": len(headlines),
            "top_headlines": headlines[:3]
        }
    except Exception:
        return {"sentiment_score": 50, "pos_count": 0, "neg_count": 0, "headline_count": 0, "top_headlines": []}


# ============================================================
# DERİN ANALİZ FONKSİYONU (Tek Hisse)
# ============================================================

def deep_analyze_stock(sym: str) -> dict:
    """
    Tek bir hisseyi tüm boyutlarıyla derinlemesine analiz eder.
    Teknik indikatörler + Formasyon + Destek/Direnç + Haber Duygusu + ML benzeri skorlama
    """
    result = {"ticker": sym, "error": None}

    # 1. Veri Çek
    df = fetch_data(sym, interval="1d", period="6mo")
    if df.empty or len(df) < 50:
        result["error"] = "Yetersiz veri"
        return result

    df = calculate_indicators(df)
    sig = generate_signals_and_score(df)

    # 2. Canlı Fiyat
    live_px = get_live_price(sym)
    if live_px <= 0:
        live_px = df['Close'].iloc[-1]

    # 3. Teknik Skor (0-100)
    tech_score = sig['score']

    # 4. Momentum Trendi (Son 5 gün ortalama RSI eğimi)
    momentum_bonus = 0
    if 'RSI_14' in df.columns and len(df) >= 6:
        rsi_last5 = df['RSI_14'].iloc[-5:].dropna()
        if len(rsi_last5) >= 2:
            rsi_slope = rsi_last5.iloc[-1] - rsi_last5.iloc[0]
            if rsi_slope > 5:
                momentum_bonus = 10
            elif rsi_slope > 0:
                momentum_bonus = 5

    # 5. Hacim Patlaması Bonusu
    volume_bonus = 0
    if len(df) >= 11:
        avg_vol = df['Volume'].iloc[-11:-1].mean()
        today_vol = df['Volume'].iloc[-1]
        if avg_vol > 0 and today_vol > avg_vol * 1.5:
            if df['Close'].iloc[-1] > df['Open'].iloc[-1]:
                volume_bonus = 15
            else:
                volume_bonus = 5

    # 6. Çoklu Zaman Dilimi Bonusu
    tf_bonus = 0
    df_1h = fetch_data(sym, interval="1h", period="1mo")
    if not df_1h.empty and len(df_1h) >= 20:
        df_1h = calculate_indicators(df_1h)
        sig_1h = generate_signals_and_score(df_1h)
        if sig['decision'] in ["Al", "Güçlü Al"] and sig_1h['decision'] in ["Al", "Güçlü Al"]:
            tf_bonus = 15
        elif sig['decision'] in ["Al", "Güçlü Al"] or sig_1h['decision'] in ["Al", "Güçlü Al"]:
            tf_bonus = 5

    # 7. Formasyon Bonusu
    pattern_bonus = 0
    pattern_text = "-"
    p_res = detect_candlestick_patterns(df)
    if p_res and p_res.get('summary') and "tespit edilmedi" not in p_res.get('summary'):
        pattern_text = p_res['summary'].splitlines()[0].replace('*', '').strip()
        if any(w in pattern_text.lower() for w in ['boğa', 'çekiç', 'yutan', 'sabah']):
            pattern_bonus = 10

    # 8. Destek Yakınlık Bonusu (Desteğe yakınsa risk düşük)
    support_bonus = 0
    zones = calculate_best_zones(df)
    dist_sup_pct = None
    dist_res_pct = None
    if zones.get('supports'):
        sup = zones['supports'][0]['price']
        dist_sup_pct = ((live_px - sup) / live_px) * 100
        if dist_sup_pct < 3:  # Desteğe %3'ten yakınsa
            support_bonus = 10
    if zones.get('resistances'):
        res_p = zones['resistances'][0]['price']
        dist_res_pct = ((res_p - live_px) / live_px) * 100

    # 9. Haber Duygu Analizi
    news = _fetch_news_sentiment(sym)
    news_bonus = 0
    if news['sentiment_score'] > 70:
        news_bonus = 10
    elif news['sentiment_score'] > 55:
        news_bonus = 5
    elif news['sentiment_score'] < 30:
        news_bonus = -10

    # 10. Dipten Dönüş Bonusu
    reversal_bonus = 0
    reversal_text = "-"
    if 'RSI_14' in df.columns and len(df) >= 3:
        rsi_today = df['RSI_14'].iloc[-1]
        rsi_yest = df['RSI_14'].iloc[-2]
        if pd.notna(rsi_today) and pd.notna(rsi_yest):
            if rsi_yest < 35 and rsi_today > rsi_yest:
                reversal_bonus = 15
                reversal_text = "🔥 Dipten Dönüş"

    # ============================================================
    # KOMPOZİT SKOR HESAPLAMA (Ağırlıklı)
    # ============================================================
    # Teknik Skor:       %40
    # Momentum:          %10
    # Hacim:             %10
    # Çoklu TF:          %10
    # Formasyon:         %5
    # Destek yakınlık:   %5
    # Haber Duygusu:     %10
    # Dipten Dönüş:      %10

    composite = (
        tech_score * 0.40 +
        (50 + momentum_bonus) * 0.10 +
        (50 + volume_bonus) * 0.10 +
        (50 + tf_bonus) * 0.10 +
        (50 + pattern_bonus) * 0.05 +
        (50 + support_bonus) * 0.05 +
        news['sentiment_score'] * 0.10 +
        (50 + reversal_bonus) * 0.10
    )
    composite = min(100, max(0, round(composite, 1)))

    # Detay sözlüğü
    rsi_val = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns and pd.notna(df['RSI_14'].iloc[-1]) else None
    macd_val = df['MACDh'].iloc[-1] if 'MACDh' in df.columns and pd.notna(df['MACDh'].iloc[-1]) else None

    result.update({
        "fiyat": round(live_px, 2),
        "sektor": get_sector(sym),
        "kompozit_skor": composite,
        "teknik_skor": tech_score,
        "karar": sig['decision'],
        "rsi": round(rsi_val, 1) if rsi_val else "-",
        "macd_hist": round(macd_val, 3) if macd_val else "-",
        "momentum_bonus": momentum_bonus,
        "volume_bonus": volume_bonus,
        "tf_bonus": tf_bonus,
        "pattern_text": pattern_text,
        "pattern_bonus": pattern_bonus,
        "support_bonus": support_bonus,
        "dist_support_pct": round(dist_sup_pct, 1) if dist_sup_pct else "-",
        "dist_resist_pct": round(dist_res_pct, 1) if dist_res_pct else "-",
        "reversal": reversal_text,
        "reversal_bonus": reversal_bonus,
        "news_sentiment": news['sentiment_score'],
        "news_pos": news['pos_count'],
        "news_neg": news['neg_count'],
        "news_headlines": news['top_headlines'],
        "news_bonus": news_bonus,
        "risk_details": sig.get('risk', {}),
        "summary": sig.get('summary', '')
    })
    return result


# ============================================================
# TOP 5 İNCELEME - ANA FONKSİYON
# ============================================================

def find_top_picks(symbol_list: list = None, top_n: int = 5, progress_bar=None) -> list:
    """
    Verilen hisse listesini derinlemesine analiz edip,
    yükselme potansiyeli en yüksek ilk N hisseyi döndürür.
    """
    if symbol_list is None:
        symbol_list = BIST30_SYMBOLS

    all_results = []
    total = len(symbol_list)

    for idx, sym in enumerate(symbol_list):
        res = deep_analyze_stock(sym)
        if res.get('error') is None:
            all_results.append(res)

        if progress_bar:
            progress_bar.progress((idx + 1) / total, text=f"🔬 {sym} derinlemesine inceleniyor... ({idx+1}/{total})")

    # Kompozit skora göre sırala ve en iyileri döndür
    all_results.sort(key=lambda x: x['kompozit_skor'], reverse=True)
    return all_results[:top_n]
