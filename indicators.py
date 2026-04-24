import pandas as pd
import numpy as np
import ta
import streamlit as st
from patterns import detect_candlestick_patterns

def calculate_vwap(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """Son N günün Hacim Ağırlıklı Ortalama Fiyatını (VWAP) hesaplar."""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).rolling(window=window).sum() / df['Volume'].rolling(window=window).sum()
    return vwap

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    'ta' kütüphanesini kullanarak 20+ teknik indikatörü veri setine ekler.
    """
    if df.empty or len(df) < 50:
         return df

    try:
        # Momentum
        df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
        
        macd = ta.trend.MACD(close=df['Close'], window_fast=12, window_slow=26, window_sign=9)
        df['MACD'] = macd.macd()
        df['MACDh'] = macd.macd_diff()
        df['MACDs'] = macd.macd_signal()
        
        stoch = ta.momentum.StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3)
        df['STOCHk_14_3_3'] = stoch.stoch()
        df['STOCHd_14_3_3'] = stoch.stoch_signal()
        
        df['ADX_14'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
        
        # Trend
        df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
        if len(df) >= 200:
            df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)
        else:
            df['SMA_200'] = np.nan
            
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
        if len(df) >= 200:
            df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
        else:
            df['EMA_200'] = np.nan

        # SuperTrend mantığı (basitleştirilmiş)
        atr_st = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=10)
        hl2 = (df['High'] + df['Low']) / 2
        df['SUPERTd_10_3.0'] = np.where(df['Close'] > hl2, 1, -1)

        # Hacim
        df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
        df['MFI_14'] = ta.volume.money_flow_index(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=14)

        # Volatilite: Bollinger & ATR
        bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BBL_20_2.0'] = bb.bollinger_lband()
        df['BBU_20_2.0'] = bb.bollinger_hband()
        df['BBM_20_2.0'] = bb.bollinger_mavg()
        df['ATRr_14'] = ta.volatility.average_true_range(high=df['High'], low=df['Low'], close=df['Close'], window=14)

        # Ichimoku Cloud (Modern)
        ichimoku = ta.trend.IchimokuIndicator(high=df['High'], low=df['Low'], window1=9, window2=26, window3=52)
        df['ICH_span_a'] = ichimoku.ichimoku_a()
        df['ICH_span_b'] = ichimoku.ichimoku_b()
        df['ICH_base'] = ichimoku.ichimoku_base_line()
        df['ICH_conv'] = ichimoku.ichimoku_conversion_line()
        
        # VWAP
        df['VWAP_5'] = calculate_vwap(df, window=5)

        return df
    except Exception:
        return df

def detect_rsi_divergence(df: pd.DataFrame, window: int = 30) -> dict:
    """Son iki tepe/dip üzerinden RSI uyumsuzluğu tespiti yapar."""
    if len(df) < window or 'RSI_14' not in df.columns:
        return {"type": "Normal", "bonus": 0, "text": ""}
    
    def find_peaks(arr):
        peaks = []
        for i in range(1, len(arr)-1):
            if arr[i] > arr[i-1] and arr[i] > arr[i+1]: peaks.append(i)
        return peaks

    def find_troughs(arr):
        troughs = []
        for i in range(1, len(arr)-1):
            if arr[i] < arr[i-1] and arr[i] < arr[i+1]: troughs.append(i)
        return troughs

    sub = df.tail(window).copy()
    prices_h = sub['High'].values
    prices_l = sub['Low'].values
    rsis = sub['RSI_14'].values
    
    # 1. Negatif Uyumsuzluk (Bearish)
    p_peaks = find_peaks(prices_h)
    if len(p_peaks) >= 2:
        i1, i2 = p_peaks[-2], p_peaks[-1]
        if prices_h[i2] > prices_h[i1] and rsis[i2] < rsis[i1]:
            return {"type": "Negatif", "bonus": -20, "text": "⚠️ Negatif Uyumsuzluk (Zirve Yorulması)"}

    # 2. Pozitif Uyumsuzluk (Bullish)
    p_troughs = find_troughs(prices_l)
    if len(p_troughs) >= 2:
        i1, i2 = p_troughs[-2], p_troughs[-1]
        if prices_l[i2] < prices_l[i1] and rsis[i2] > rsis[i1]:
            return {"type": "Pozitif", "bonus": 20, "text": "🔥 Pozitif Uyumsuzluk (Dipte Alım Gücü)"}
                
    return {"type": "Normal", "bonus": 0, "text": ""}

def check_volatility_squeeze(df: pd.DataFrame) -> dict:
    """Bollinger Bantları Keltner Kanallarının içine girerse Squeeze (Sıkışma) vardır."""
    if len(df) < 20 or 'BBU_20_2.0' not in df.columns:
        return {"squeeze": False, "text": ""}
    
    # Keltner Channel hesapla (Basit)
    atr = df['ATRr_14']
    ema20 = df['EMA_20']
    kc_upper = ema20 + (1.5 * atr)
    kc_lower = ema20 - (1.5 * atr)
    
    bb_upper = df['BBU_20_2.0']
    bb_lower = df['BBL_20_2.0']
    
    is_squeeze = (bb_upper < kc_upper).iloc[-1] and (bb_lower > kc_lower).iloc[-1]
    rsi_val = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else 0
    
    if is_squeeze and rsi_val > 50:
        return {"squeeze": True, "text": "⚡ Bollinger Squeeze + RSI > 50: Patlamaya Hazır!"}
    elif is_squeeze:
        return {"squeeze": True, "text": "⚡ Bollinger Squeeze Tespit Edildi."}
    return {"squeeze": False, "text": ""}

def detect_liquidity_sweep(df: pd.DataFrame, window: int = 20) -> dict:
    """Akıllı Para (SMC) Stop Avı / Liquidity Sweep Tespiti."""
    if len(df) < window + 2:
        return {"detected": False, "score": 0, "text": ""}
    
    # Son 20 günün dip seviyesi (dün itibariyle)
    recent_low = df['Low'].iloc[-(window+1):-1].min()
    today = df.iloc[-1]
    
    # Bugün o dibin altına inmiş (Sweep) ama güçlü kapatmış (Pinbar/Spring)
    if today['Low'] < recent_low and today['Close'] > recent_low:
        # Kapanış, en düşük seviyeden belirgin şekilde yukarıdaysa (Gövde yukarda kapattıysa)
        range_px = today['High'] - today['Low']
        if range_px > 0:
            lower_shadow = (min(today['Open'], today['Close']) - today['Low']) / range_px
            if lower_shadow > 0.4:
                return {"detected": True, "score": 20, "text": "🎯 Likidite Süpürme (SMC - Stop Avı) Tespit Edildi!"}
                
    return {"detected": False, "score": 0, "text": ""}

def calculate_obv_divergence(df: pd.DataFrame, window: int = 10) -> dict:
    """Fiyatın yatay/düşüşte, OBV'nin yüksek olmasını tespit eder (Kurumsal Toplama)."""
    if len(df) < window or 'OBV' not in df.columns:
        return {"detected": False, "score": 0, "text": ""}
        
    sub = df.tail(window)
    price_change = (sub['Close'].iloc[-1] - sub['Close'].iloc[0]) / sub['Close'].iloc[0] * 100
    obv_change = (sub['OBV'].iloc[-1] - sub['OBV'].iloc[0]) / abs(sub['OBV'].iloc[0]) * 100 if sub['OBV'].iloc[0] != 0 else 0
    
    if price_change < 1.0 and obv_change > 5.0:
        return {"detected": True, "score": 15, "text": "🐋 OBV Diverjansı (Gizli Kurumsal Toplama Onayı)"}
        
    return {"detected": False, "score": 0, "text": ""}

def calculate_volume_confirmation(df: pd.DataFrame, is_bear: bool = False) -> dict:
    """Hacim Onayı (Volume Confirmation). Ayı piyasasında daha sert kriter (2.5x) uygular."""
    if len(df) < 21:
        return {"status": "Normal", "ratio": 1.0}
    avg_vol = df['Volume'].iloc[-21:-1].mean()
    if avg_vol == 0: return {"status": "Normal", "ratio": 1.0}
    last_vol = df['Volume'].iloc[-1]
    ratio = last_vol / avg_vol
    
    threshold = 2.5 if is_bear else 1.8
    if ratio > threshold:
        return {"status": "🔥 Hacim Patlaması", "ratio": ratio}
    elif ratio > 1.3:
        return {"status": "🌊 Güçlü Hacim", "ratio": ratio}
    return {"status": "Normal", "ratio": ratio}

def check_bottom_reversal(df: pd.DataFrame) -> dict:
    """
    Ayı piyasası özel: RSI < 35 + Bollinger Alt Bant Teması + Çekiç Formasyonu.
    """
    if len(df) < 20: return {"detected": False, "score": 0}
    last = df.iloc[-1]
    
    # 1. Aşırı Satım
    rsi_cond = last.get('RSI_14', 50) < 35
    # 2. Bollinger Band Teması
    bb_cond = last['Low'] <= last.get('BBL_20_2.0', 0)
    # 3. Formasyon tespiti
    p_res = detect_candlestick_patterns(df)
    hammer_cond = "Çekiç" in p_res.get('summary', '')
    
    if rsi_cond and bb_cond and hammer_cond:
        return {"detected": True, "score": 30, "text": "🔥 Gelişmiş Dipten Dönüş (RSI+BB+Pattern)"}
    elif rsi_cond and bb_cond:
        return {"detected": True, "score": 15, "text": "🛡️ Güçlü Destek Dönüşü (RSI+BB)"}
        
    return {"detected": False, "score": 0}

def get_market_regime(xu100_df: pd.DataFrame) -> dict:
    """BIST 100 endeksine bakarak piyasa rejimini (Ayı/Boğa) belirler."""
    if xu100_df is None or xu100_df.empty or len(xu100_df) < 50:
        return {"mode": "Normal", "is_bear": False, "daily_chg": 0.0, "rsi": 50.0}
    
    try:
        xu100_df = calculate_indicators(xu100_df)
        last = xu100_df.iloc[-1]
        prev = xu100_df.iloc[-2]
        
        c_last = float(last['Close'])
        c_prev = float(prev['Close'])
        c_5d_ago = float(xu100_df['Close'].iloc[-5]) if len(xu100_df) >= 5 else c_prev
        
        daily_chg = ((c_last - c_prev) / c_prev) * 100.0 if c_prev != 0 else 0.0
        chg_5d = ((c_last - c_5d_ago) / c_5d_ago) * 100.0 if c_5d_ago != 0 else 0.0

        
        ema50 = float(last.get('EMA_50', 0.0))
        ema200 = float(last.get('EMA_200', 0.0))
        rsi = float(last.get('RSI_14', 50.0))
        
        is_bear = c_last < ema50
        
        # Garanti atama
        regime_mode = "⚖️ TESTEREYE PİYASASI"
        
        if daily_chg < -2.0:
            regime_mode = "🛑 KRİTİK AYI (Sert Satış)"
        elif is_bear:
            regime_mode = "⚠️ AYI PİYASASI (Temkinli)"
        elif c_last > ema50 and c_last > ema200:
            regime_mode = "🚀 BOĞA PİYASASI (Agresif)"
            
        return {
            "mode": regime_mode,
            "is_bear": is_bear,
            "daily_chg": round(daily_chg, 2),
            "xu100_5d_chg": round(chg_5d, 2),
            "rsi": round(rsi, 1)
        }
    except Exception:
        # Kodun çökmesini engelleyen güvenli dönüş
        return {"mode": "Bilinmeyen", "is_bear": False, "daily_chg": 0.0, "xu100_5d_chg": 0.0, "rsi": 50.0}

from takas_engine import get_takas_data

def generate_signals_and_score(df: pd.DataFrame, ticker: str = "", market_regime: dict = None, sentiment_score: float = 0.0) -> dict:
    """
    Teknik sinyallerle Haber Duygu (Sentiment) verisini ve Takas Verisini birleştiren 
    Hibrit Karar Mekanizması.
    """
    if df.empty or len(df) < 2:
        return {"score": 0, "pgs": 50, "decision": "Veri Yetersiz", "details": {}, "summary": "", "risk": {}}

    is_bear = market_regime['is_bear'] if market_regime else False
    last = df.iloc[-1]
    close_price = last.get('Close', 0)
    signals = {"Trend": {}, "Momentum": {}, "Volume": {}}
    summary = []
    
    try:
        # --- 1. TEKNİK ANALİZ BÖLÜMÜ ---
        # (EMA, Ichimoku, RSI, MFI vb. hesaplamalar aynı kalıyor)
        if pd.notna(last.get('EMA_200')):
            signals['Trend']['EMA200'] = 1 if close_price > last['EMA_200'] else -1
        if pd.notna(last.get('EMA_50')):
            signals['Trend']['EMA50'] = 1 if close_price > last['EMA_50'] else -1
            
        ich_a = last.get('ICH_span_a', 0)
        ich_b = last.get('ICH_span_b', 0)
        ich_base = last.get('ICH_base', 0)
        ich_conv = last.get('ICH_conv', 0)
        if ich_a > 0 and ich_b > 0:
            ich_cloud_top = max(ich_a, ich_b)
            ich_cloud_bottom = min(ich_a, ich_b)
            # Ichimoku Bulutu = Ana Yön (Trend Filtresi)
            if close_price > ich_cloud_top: 
                signals['Trend']['Ichimoku'] = 1
                summary.append("☁️ Ichimoku: Fiyat bulut üzerinde, **Ana Yön Pozitif**.")
            elif close_price < ich_cloud_bottom: 
                signals['Trend']['Ichimoku'] = -1
                summary.append("☁️ Ichimoku: Fiyat bulut altında, **Ana Yön Negatif**.")
            else: 
                signals['Trend']['Ichimoku'] = 0
                summary.append("☁️ Ichimoku: Fiyat bulut içinde, Yatay/Kararsız bölge.")
            
            # Ichimoku Kesişimi = Tetikleyici (Trigger)
            if ich_conv > ich_base: 
                signals['Trend']['Ichimoku_Cross'] = 0.5
                summary.append("⚡ Ichimoku: Tenkan-sen/Kijun-sen kesişimi **Alış Tetiklendi**.")
            elif ich_conv < ich_base: 
                signals['Trend']['Ichimoku_Cross'] = -0.5
            
        rsi_val = last.get('RSI_14', 50)
        if is_bear:
            if rsi_val > 60: signals['Momentum']['RSI'] = -1 
            elif rsi_val < 25: signals['Momentum']['RSI'] = 1.5
            elif 25 < rsi_val < 40: signals['Momentum']['RSI'] = 1
            else: signals['Momentum']['RSI'] = 0
        else:
            if rsi_val > 75: signals['Momentum']['RSI'] = -0.5
            elif rsi_val < 45: signals['Momentum']['RSI'] = 1
            else: signals['Momentum']['RSI'] = 0.5
            
        vol_conf = calculate_volume_confirmation(df, is_bear=is_bear)
        signals['Volume']['Conf'] = 1 if "Hacim Patlaması" in vol_conf['status'] else 0.5 if "Güçlü" in vol_conf['status'] else -0.5
        
        mfi_val = last.get('MFI_14', 50)
        if mfi_val > 55: 
            signals['Volume']['MFI'] = 1
            summary.append("💰 **Para Giriş Onayı:** MFI > 55 seviyesinde, hissede gerçek para birikimi var.")
        elif mfi_val < 45:
            signals['Volume']['MFI'] = -1
            summary.append("💸 **Para Çıkış Uyarısı:** MFI 45 altına kaydı, likidite azalıyor.")

        def calc_cat_score(cat_dict):
            if not cat_dict: return 50
            vals = list(cat_dict.values())
            return (sum(vals) / len(vals) + 1) * 50

        t_score = calc_cat_score(signals['Trend'])
        m_score = calc_cat_score(signals['Momentum'])
        v_score = calc_cat_score(signals['Volume'])
        
        reversal = check_bottom_reversal(df)
        reversal_bonus = reversal['score'] if is_bear else 0
        div_res = detect_rsi_divergence(df)
        if div_res['text']: summary.append(div_res['text'])
        sqz_res = check_volatility_squeeze(df)
        if sqz_res['text']: summary.append(sqz_res['text'])

        # TEKNİK TOPLAM SKOR (%70 Ağırlık için baz)
        tech_total = (t_score * 0.40) + (m_score * 0.40) + (v_score * 0.20) + reversal_bonus + div_res['bonus']
        tech_total = min(100, max(0, tech_total))

        # --- 2. HİBRİT SKORLAMA (%70 Teknik + %30 Duygu) ---
        # sentiment_score -1 ile +1 arası gelir. Onu 0-100 arasına çekelim.
        sent_normalized = (sentiment_score + 1) * 50
        
        # Hibrit Formül
        final_score = (tech_total * 0.70) + (sent_normalized * 0.30)
        final_score = round(min(100, max(0, final_score)), 1)

        # Karar Mekanizması
        if final_score >= 70: 
            decision = "Güçlü Al"
        elif final_score >= 55: decision = "Al"
        elif final_score <= 30: decision = "Güçlü Sat"
        else: decision = "Nötr"

        # --- 3. GÜÇLÜ ONAY TEYİDİ ---
        # Eğer teknik AL diyorsa ve haber duygusu ÇOK POZİTİF (+0.6 üstü) ise
        if decision in ["Al", "Güçlü Al"] and sentiment_score > 0.6:
            conviction_level = "GÜÇLÜ ONAY 💎"
            summary.append("💎 Hibrit Teyit: Teknik sinyal ve haber akışı tam uyumlu (Güçlü Onay).")
        else:
            # Standart PGS tabanlı güven seviyesi
            # PGS hesaplama
            pgs_score = 100
            range_px = (last['High'] - last['Low'])
            upper_shadow_ratio = (last['High'] - last['Close']) / range_px if range_px > 0 else 0
            if upper_shadow_ratio > 0.4: pgs_score -= (upper_shadow_ratio - 0.4) * 80
            if vol_conf['ratio'] < 1.3: pgs_score -= 15
            ema20 = last.get('EMA_20', 0)
            dist_ema20 = (close_price - ema20) / ema20 if ema20 > 0 else 0
            if dist_ema20 > 0.12: pgs_score -= (dist_ema20 - 0.12) * 200
            if rsi_val > 65: pgs_score -= (rsi_val - 65) * 1.5
            
            # Takas Teyidi (Yabancı Payı ve Değişim Modeli)
            if ticker:
                takas = get_takas_data(ticker)
                fr_ratio = takas.get('foreign_ratio', 0)
                d_chg = takas.get('daily_change', 0)
                
                if fr_ratio > 25.0 and d_chg > 0:
                    pgs_score += 10 # Ciddi Yabancı Takas güvencesi var
                    summary.append(f"🏦 Takas Teyidi Pozitif: Yabancı Payı (%{fr_ratio:.1f}) Artıyor (+%{d_chg:.2f})")
                elif d_chg < -1.0:
                    pgs_score -= 10 # Yabancı çıkışı
                    summary.append(f"⚠️ Takas Uyarı: Yabancı çıkışı var (-%{abs(d_chg):.2f})")
            
            pgs_score = round(max(0, min(100, pgs_score)), 1)

            if final_score > 75 and pgs_score > 75: conv_level = "YÜKSEK 🚀"
            elif final_score > 55 and pgs_score > 55: conv_level = "ORTA ⚖️"
            else: conv_level = "DÜŞÜK ⚠️"
            conviction_level = conv_level

        # ... (Diğer etiketleme ve terminoloji revizyonları aynı kalabilir)
        label_map = {
            "Güçlü Al": "🚀 Momentum Lideri", "Al": "📈 Pozitif Trend",
            "Güçlü Sat": "🛑 Agresif Negatif", "Sat": "📉 Negatif Baskı",
            "Nötr": "⚖️ Nötr / Konsolidasyon"
        }
        decision = label_map.get(decision, decision)
        if reversal['detected']: decision = "🔥 Tepki Potansiyeli"
        
        # Risk / ATR
        atr = last.get('ATRr_14', close_price * 0.03)
        risk = {
            "SL": round(close_price - (atr * 1.5), 2),
            "TP1": round(close_price + (atr * 3.0), 2),
            "TP2": round(close_price + (atr * 5.0), 2)
        }

        return {
            "score": final_score,
            "pgs": pgs_score if 'pgs_score' in locals() else 50,
            "decision": decision,
            "conviction_level": conviction_level,
            "details": {"Teknik": round(tech_total,1), "Duygu": round(sent_normalized,1)},
            "summary": "\n".join(summary),
            "risk": risk
        }
    except Exception as e:
        return {"score": 50, "pgs": 50, "decision": "Hata", "summary": str(e), "risk": {}, "details": {}}
