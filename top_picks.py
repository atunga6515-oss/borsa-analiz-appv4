import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sqlite3
import json
import os
from datetime import datetime
from data_loader import fetch_data, get_live_price
from indicators import (calculate_indicators, generate_signals_and_score, 
                        calculate_volume_confirmation, check_bottom_reversal, get_market_regime)
from kap_news import get_sentiment_summary
from fundamental_analyzer import get_fundamental_data
from patterns import detect_candlestick_patterns
from support_resistance import calculate_best_zones
from screener import get_sector, BIST30_SYMBOLS, BIST100_SYMBOLS, BIST_ALL_SYMBOLS

# Veritabanı Yolu
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def _get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS top_picks_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            run_date TEXT NOT NULL,
            results_json TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def save_top_picks_history(username: str, results: list):
    """Top 5 sonuçlarını veritabanına JSON olarak kaydeder."""
    if not results:
        return
    conn = _get_db_conn()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        "INSERT INTO top_picks_history (username, run_date, results_json) VALUES (?, ?, ?)",
        (username, now_str, json.dumps(results))
    )
    conn.commit()
    conn.close()

def get_top_picks_history_dates(username: str) -> list:
    """Kaydedilmiş analiz tarihlerini döndürür."""
    conn = _get_db_conn()
    cursor = conn.execute(
        "SELECT DISTINCT run_date FROM top_picks_history WHERE username=? ORDER BY run_date DESC",
        (username,)
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates

def get_top_picks_by_date(username: str, run_date: str) -> list:
    """Belirli bir tarihteki analiz sonuçlarını döndürür."""
    conn = _get_db_conn()
    cursor = conn.execute(
        "SELECT results_json FROM top_picks_history WHERE username=? AND run_date=?",
        (username, run_date)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []


# Eski kelime bazlı sentiment fonksiyonu kaldırıldı (kap_news modülüne taşındı)


# ============================================================
# DERİN ANALİZ FONKSİYONU (Tek Hisse)
# ============================================================

def deep_analyze_stock(sym: str, market_regime: dict = None) -> dict:
    """
    Tek bir hisseyi tüm boyutlarıyla derinlemesine analiz eder.
    Teknik indikatörler + Formasyon + Destek/Direnç + Haber Duygusu + ML benzeri skorlama
    """
    result = {"ticker": sym, "error": None, "summary": ""}

    # 1. Veri Çek
    df = fetch_data(sym, interval="1d", period="6mo")
    if df.empty or len(df) < 50:
        result["error"] = "Yetersiz veri"
        return result

    # 1.1 Haber Duygusu Çek (Gemini AI)
    sent_score, news_list = get_sentiment_summary(sym)
    sent_100 = (sent_score + 1) * 50
    
    df = calculate_indicators(df)
    sig = generate_signals_and_score(df, market_regime=market_regime, sentiment_score=sent_score)

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
    
    if zones.get('best_buy_zones'):
        # [(Name, Price), ...] formatında geliyor, ilk elemanın fiyatını (index 1) al
        sup = zones['best_buy_zones'][0][1]
        dist_sup_pct = ((live_px - sup) / live_px) * 100
        if dist_sup_pct < 3:  # Desteğe %3'ten yakınsa
            support_bonus = 10
            
    if zones.get('best_sell_zones'):
        res_p = zones['best_sell_zones'][0][1]
        dist_res_pct = ((res_p - live_px) / live_px) * 100

    # 9. Haber Duygu Analizi (AI Sonuçlarını Kullan)
    news_bonus = 0
    is_bear = market_regime['is_bear'] if market_regime else False
    price_below_sma50 = live_px < df['SMA_50'].iloc[-1] if 'SMA_50' in df.columns else False

    if sent_100 > 70:
        news_bonus = 5 if (is_bear and price_below_sma50) else 10
    elif sent_100 > 55:
        news_bonus = 2 if (is_bear and price_below_sma50) else 5
    elif sent_100 < 30:
        news_bonus = -15 if is_bear else -10

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
    # KOMPOZİT SKOR HESAPLAMA (Geliştirilmiş Ağırlıklı)
    # ============================================================
    # Teknik Skor:       %35 (Düşürüldü)
    # Momentum:          %10
    # Hacim:             %10
    # Çoklu TF:          %10
    # Formasyon:         %5
    # Destek yakınlık:   %5
    # Haber Duygusu:     %20 (Artırıldı - KAP Etkisi)
    # Dipten Dönüş:      %10

    composite = (
        tech_score * 0.35 +
        (50 + momentum_bonus) * 0.10 +
        (50 + volume_bonus) * 0.10 +
        (50 + tf_bonus) * 0.10 +
        (50 + pattern_bonus) * 0.05 +
        (50 + support_bonus) * 0.05 +
        sent_100 * 0.20 +
        (50 + reversal_bonus) * 0.10
    )
    
    # 11. Yeni Filtreler (Gölge Analizi & Overextension)
    range_px = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    if range_px > 0:
        upper_shadow = (df['High'].iloc[-1] - df['Close'].iloc[-1]) / range_px
        if upper_shadow > 0.5:
            composite *= 0.85
            result["summary"] += "\n⚠️ Üst fitil baskısı (Zirve Reddi) tespit edildi."

    ema20 = df['EMA_20'].iloc[-1] if 'EMA_20' in df.columns else 0
    if ema20 > 0:
        dist_ema20 = (live_px - ema20) / ema20
        if dist_ema20 > 0.12:
            composite *= 0.9
            result["summary"] += f"\n🧲 EMA 20'den çok uzak (%{dist_ema20*100:.1f}), düzeltme riski."

    # Ayı Piyasası & SMA 50 Penaltısı (Tedarikçi Koruması)
    if is_bear and price_below_sma50:
        composite *= 0.85 

    composite = min(100, max(0, round(composite, 1)))
    
    # Karar Mekanizması RSI Doygunluk Güncellemesi
    karar = sig['decision']
    if composite >= 70 and 'RSI_14' in df.columns and df['RSI_14'].iloc[-1] > 65:
        karar = "🧘 Doygunluk Bölgesi"
        result["summary"] += "\n🧘 RSI Doygunluğu: Kar satışı gelebilir."
    
    # Endeks Acil Freni
    if market_regime and market_regime.get('daily_chg', 0) < -2.0:
        if any(w in karar for w in ["Trend", "Lideri", "Potansiyeli"]):
            karar = "⚠️ Bekle (Endeks Freni)"
        
    # V6 HİBRİT SKOR ENTEGRASYONU
    try:
        fund_data = get_fundamental_data(sym)
        tem_skor = fund_data.get('fundamental_score', 50)
    except Exception:
        fund_data = {"pe": 0, "pb": 0, "div_yield": 0, "fundamental_score": 50, "status": "Veri Yok"}
        tem_skor = 50
    
    # V6 Hibrit Skor: %60 Teknik Kompozit + %40 Temel Not
    v6_score = round((composite * 0.6) + (tem_skor * 0.4), 1)

    # Detay sözlüğü
    rsi_val = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns and pd.notna(df['RSI_14'].iloc[-1]) else None
    macd_val = df['MACDh'].iloc[-1] if 'MACDh' in df.columns and pd.notna(df['MACDh'].iloc[-1]) else None

    result.update({
        "fiyat": round(live_px, 2),
        "sektor": get_sector(sym),
        "kompozit_skor": v6_score,
        "V6 Hibrit Skor": v6_score,
        "teknik_skor": composite,
        "temel_skor": tem_skor,
        "pe": fund_data.get('pe', 0),
        "pb": fund_data.get('pb', 0),
        "div_yield": fund_data.get('div_yield', 0),
        "temel_durum": fund_data.get('status', 'Normal'),
        "graham_value": fund_data.get('graham_value', 0),
        "pgs": sig.get('pgs', 50),
        "karar": karar,
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
        "news_sentiment": round(sent_100, 1),
        "news_pos": len([x for x in news_list if x['score'] > 0]),
        "news_neg": len([x for x in news_list if x['score'] < 0]),
        "news_headlines": [x['title'] for x in news_list[:3]],
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

    # Market Rejimi Hesapla (Bir kere)
    xu100_df = fetch_data("XU100", interval="1d", period="1y")
    market_regime = get_market_regime(xu100_df)

    all_results = []
    total = len(symbol_list)

    for idx, sym in enumerate(symbol_list):
        res = deep_analyze_stock(sym, market_regime=market_regime)
        if res.get('error') is None:
            all_results.append(res)

        if progress_bar:
            progress_bar.progress((idx + 1) / total, text=f"🔬 {sym} derinlemesine inceleniyor... ({idx+1}/{total})")

    # Kompozit skora göre sırala ve en iyileri döndür
    all_results.sort(key=lambda x: x['kompozit_skor'], reverse=True)
    return all_results[:top_n]
