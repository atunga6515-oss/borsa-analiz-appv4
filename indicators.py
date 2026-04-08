import pandas as pd
import numpy as np
import ta
import streamlit as st
from patterns import detect_candlestick_patterns

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
        
        df['CCI_20'] = ta.trend.cci(high=df['High'], low=df['Low'], close=df['Close'], window=20)
        df['ROC_10'] = ta.momentum.roc(close=df['Close'], window=10)
        df['WILLR_14'] = ta.momentum.williams_r(high=df['High'], low=df['Low'], close=df['Close'], lbp=14)

        # Trend
        df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
        if len(df) >= 200:
            df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)
        else:
            df['SMA_200'] = np.nan
            
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)

        adx = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['ADX_14'] = adx.adx()
        df['DMP_14'] = adx.adx_pos()
        df['DMN_14'] = adx.adx_neg()

        atr_st = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=10)
        hl2 = (df['High'] + df['Low']) / 2
        df['SUPERTd_10_3.0'] = np.where(df['Close'] > hl2, 1, -1)

        # Hacim
        df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
        df['CMF_20'] = ta.volume.chaikin_money_flow(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=20)
        df['MFI_14'] = ta.volume.money_flow_index(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=14)
        df['VWAP'] = ta.volume.volume_weighted_average_price(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=14)

        # Volatilite: Bollinger & ATR
        bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BBL_20_2.0'] = bb.bollinger_lband()
        df['BBU_20_2.0'] = bb.bollinger_hband()
        df['BBM_20_2.0'] = bb.bollinger_mavg()
        df['ATRr_14'] = ta.volatility.average_true_range(high=df['High'], low=df['Low'], close=df['Close'], window=14)

        return df
    except Exception as e:
        return df

def generate_signals_and_score(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 2:
        return {"score": 0, "decision": "Veri Yetersiz", "details": {}, "summary": "", "risk": {}}

    last = df.iloc[-1]
    prev = df.iloc[-2]
    close_price = last.get('Close', 0)

    signals = {"Trend": {}, "Momentum": {}, "Volume": {}}
    
    try:
        # --- TREND (Ağırlık %40) ---
        if pd.notna(last.get('SMA_20')) and pd.notna(last.get('SMA_50')):
            signals['Trend']['SMA_Cross'] = 1 if last['SMA_20'] > last['SMA_50'] else -1
            
        if pd.notna(last.get('SMA_20')):
            signals['Trend']['Price_vs_SMA20'] = 1 if close_price > last['SMA_20'] else -1

        st_dir_col = 'SUPERTd_10_3.0'
        if pd.notna(last.get(st_dir_col)):
            signals['Trend']['SuperTrend'] = last[st_dir_col]

        adx_col, dmp_col, dmn_col = 'ADX_14', 'DMP_14', 'DMN_14'
        if pd.notna(last.get(adx_col)):
            if last[adx_col] > 25:
                signals['Trend']['ADX'] = 1 if last[dmp_col] > last[dmn_col] else -1
            else:
                signals['Trend']['ADX'] = 0

        # --- MOMENTUM (Ağırlık %30) ---
        rsi_col = 'RSI_14'
        if pd.notna(last.get(rsi_col)):
            rsi = last[rsi_col]
            if rsi > 70: signals['Momentum']['RSI'] = -1
            elif rsi < 30: signals['Momentum']['RSI'] = 1
            elif rsi > 50: signals['Momentum']['RSI'] = 0.5
            else: signals['Momentum']['RSI'] = -0.5

        macdh_col = 'MACDh'
        if pd.notna(last.get(macdh_col)):
            signals['Momentum']['MACD'] = 1 if last[macdh_col] > 0 else -1

        stoch_k, stoch_d = 'STOCHk_14_3_3', 'STOCHd_14_3_3'
        if pd.notna(last.get(stoch_k)):
            k_val = last[stoch_k]
            d_val = last[stoch_d]
            if k_val < 20 and k_val > d_val: signals['Momentum']['Stoch'] = 1
            elif k_val > 80 and k_val < d_val: signals['Momentum']['Stoch'] = -1
            else: signals['Momentum']['Stoch'] = 0

        # --- HACİM (Ağırlık %30) ---
        obv_col = 'OBV'
        if pd.notna(last.get(obv_col)):
            signals['Volume']['OBV'] = 1 if last[obv_col] > prev[obv_col] else -1

        cmf_col = 'CMF_20'
        if pd.notna(last.get(cmf_col)):
            signals['Volume']['CMF'] = 1 if last[cmf_col] > 0 else -1

        def calc_cat_score(cat_dict):
            if not cat_dict: return 50
            vals = list(cat_dict.values())
            score_avg = sum(vals) / len(vals)
            return (score_avg + 1) * 50

        trend_score = calc_cat_score(signals['Trend'])
        mom_score = calc_cat_score(signals['Momentum'])
        vol_score = calc_cat_score(signals['Volume'])

        total_score = (trend_score * 0.40) + (mom_score * 0.30) + (vol_score * 0.30)
        
        if total_score >= 70: decision = "Güçlü Al"
        elif total_score >= 55: decision = "Al"
        elif total_score <= 30: decision = "Güçlü Sat"
        elif total_score <= 45: decision = "Sat"
        else: decision = "Nötr"

        # Metin Raporlama + FORMASYON TESPİTİ
        summary_lines = []
        
        # 1. Klasik Raporlama
        if rsi_col and pd.notna(last.get(rsi_col)):
            if last[rsi_col] < 30: summary_lines.append("Hisse RSI bazında **aşırı satım** bölgesinde.")
            elif last[rsi_col] > 70: summary_lines.append("Hisse RSI bazında **aşırı alım** bölgesinde.")
             
        if signals['Trend'].get('SMA_Cross') == 1:
            summary_lines.append("Har. Ortalamalarda pozitif kesişim mevcut (Trend yukarı).")
            
        # 2. Mum Formasyon Analizi
        pattern_res = detect_candlestick_patterns(df)
        if pattern_res.get('summary') and "tespit edilmedi" not in pattern_res.get('summary'):
            summary_lines.append("\n**🎯 Formasyon Analizi:**\n" + pattern_res['summary'])

        summary_text = "\n".join(summary_lines)
        if not summary_text.strip():
            summary_text = "Fiyatlarda stabilite hakim, belirgin bir ayrışma/formasyon görülmüyor."

        # Risk Management 
        atr_col = 'ATRr_14'
        risk = {}
        if atr_col and pd.notna(last.get(atr_col)):
            atr = last[atr_col]
            risk['SL'] = close_price - (2 * atr)
            risk['TP1'] = close_price * 1.05
            risk['TP2'] = close_price * 1.10
            risk['ATR'] = atr

    except Exception as e:
        return {"score": 50, "decision": "Hata", "details": {}, "summary": str(e), "risk": {}}

    return {
        "score": round(total_score, 1),
        "decision": decision,
        "details": {"Trend": round(trend_score,1), "Momentum": round(mom_score,1), "Hacim": round(vol_score,1)},
        "summary": summary_text,
        "risk": risk
    }
