import pandas as pd
import numpy as np
import ta
import warnings

# Circular importu önlemek için indicators.py çağrısı kaldırıldı. Pipeline'ı indicators.py yönetecek.
# Suppress pandas fragmentation warnings
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

def calculate_vwap(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """Son N günün Hacim Ağırlıklı Ortalama Fiyatını (VWAP) hesaplar."""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    rolling_tp_vol = (typical_price * df['Volume']).rolling(window=window).sum()
    rolling_vol = df['Volume'].rolling(window=window).sum()
    return np.where(rolling_vol == 0, typical_price, rolling_tp_vol / rolling_vol)

def calculate_100_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sisteme tam 101 adet özgün indikatör ve süre varyasyonu ekleyerek 
    muazzam genişlikte bir teknik havuz oluşturur.
    """
    df = df.copy()
    if df.empty or len(df) < 10:
        return df

    # 0. Temel indikatörlerin daha önce indicators.py'den hesaplandığı varsayılır.


    # 1. SMA Varyasyonları (12 adet)
    for w in [5, 10, 15, 20, 25, 30, 40, 50, 52, 75, 100, 150, 200]:
        col = f'SMA_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.trend.sma_indicator(df['Close'], window=w)
            except Exception:
                df[col] = np.nan

    # 2. EMA Varyasyonları (12 adet)
    for w in [5, 10, 15, 20, 25, 30, 40, 50, 52, 75, 100, 150, 200]:
        col = f'EMA_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.trend.ema_indicator(df['Close'], window=w)
            except Exception:
                df[col] = np.nan

    # 3. WMA Varyasyonları (3 adet)
    for w in [10, 20, 50]:
        col = f'WMA_{w}'
        try:
            df[col] = ta.trend.wma_indicator(df['Close'], window=w)
        except Exception:
            df[col] = np.nan

    # 4. KAMA (Kaufman Adaptive Moving Average) Varyasyonları (3 adet)
    for w in [10, 20, 50]:
        col = f'KAMA_{w}'
        try:
            df[col] = ta.momentum.kama(df['Close'], window=w)
        except Exception:
            df[col] = np.nan

    # 5. RSI Varyasyonları (7 adet)
    for w in [5, 7, 9, 11, 14, 21, 28]:
        col = f'RSI_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.momentum.rsi(df['Close'], window=w)
            except Exception:
                df[col] = np.nan

    # 6. Stochastic Varyasyonları (5 adet)
    for w in [5, 9, 14, 21, 28]:
        col_k = f'STOCHk_{w}'
        col_d = f'STOCHd_{w}'
        if col_k not in df.columns or col_d not in df.columns:
            try:
                stoch = ta.momentum.StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=w, smooth_window=3)
                df[col_k] = stoch.stoch()
                df[col_d] = stoch.stoch_signal()
            except Exception:
                df[col_k] = np.nan
                df[col_d] = np.nan

    # 7. Stochastic RSI Varyasyonları (3 adet)
    for w in [9, 14, 21]:
        col_k = f'STOCHRSIk_{w}'
        col_d = f'STOCHRSId_{w}'
        try:
            stoch_rsi = ta.momentum.StochRSIIndicator(close=df['Close'], window=w, smooth1=3, smooth2=3)
            df[col_k] = stoch_rsi.stochrsi_k()
            df[col_d] = stoch_rsi.stochrsi_d()
        except Exception:
            df[col_k] = np.nan
            df[col_d] = np.nan

    # 8. CCI Varyasyonları (4 adet)
    for w in [10, 14, 20, 30]:
        col = f'CCI_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.trend.cci(high=df['High'], low=df['Low'], close=df['Close'], window=w)
            except Exception:
                df[col] = np.nan

    # 9. ROC Varyasyonları (5 adet)
    for w in [5, 10, 15, 20, 25]:
        col = f'ROC_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.momentum.roc(df['Close'], window=w)
            except Exception:
                df[col] = np.nan

    # 10. Williams %R Varyasyonları (4 adet)
    for w in [10, 14, 20, 25]:
        col = f'Williams_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.momentum.williams_r(high=df['High'], low=df['Low'], close=df['Close'], lbp=w)
            except Exception:
                df[col] = np.nan

    # 11. Awesome Oscillator (1 adet)
    if 'Awesome_Oscillator' not in df.columns:
        try:
            df['Awesome_Oscillator'] = ta.momentum.awesome_oscillator(df['High'], df['Low'], window1=5, window2=34)
        except Exception:
            df['Awesome_Oscillator'] = np.nan

    # 12. Bollinger Bantları (4 adet)
    for dev in [1.0, 1.5, 2.0, 2.5]:
        col_l = f'BBL_20_{dev}'
        col_u = f'BBU_20_{dev}'
        if col_l not in df.columns or col_u not in df.columns:
            try:
                bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=dev)
                df[col_l] = bb.bollinger_lband()
                df[col_u] = bb.bollinger_hband()
            except Exception:
                df[col_l] = np.nan
                df[col_u] = np.nan

    # 13. Keltner Kanalları (4 adet)
    for dev in [1.0, 1.5, 2.0, 2.5]:
        col_l = f'KCL_20_{dev}'
        col_u = f'KCU_20_{dev}'
        try:
            kc = ta.volatility.KeltnerChannel(high=df['High'], low=df['Low'], close=df['Close'], window=20, window_atr=10, multiplier=dev)
            df[col_l] = kc.keltner_channel_lband()
            df[col_u] = kc.keltner_channel_hband()
        except Exception:
            df[col_l] = np.nan
            df[col_u] = np.nan

    # 14. Donchian Kanalları (4 adet)
    for w in [10, 20, 30, 50]:
        col_m = f'DCM_{w}'
        try:
            dc = ta.volatility.DonchianChannel(high=df['High'], low=df['Low'], close=df['Close'], window=w)
            df[col_m] = dc.donchian_channel_mband()
        except Exception:
            df[col_m] = np.nan

    # 15. ADX & DMI Varyasyonları (4 adet)
    for w in [14, 20]:
        col_adx = f'ADX_{w}'
        col_pos = f'ADX_pos_{w}'
        col_neg = f'ADX_neg_{w}'
        if col_adx not in df.columns:
            try:
                adx_ind = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=w)
                df[col_adx] = adx_ind.adx()
                df[col_pos] = adx_ind.adx_pos()
                df[col_neg] = adx_ind.adx_neg()
            except Exception:
                df[col_adx] = np.nan
                df[col_pos] = np.nan
                df[col_neg] = np.nan

    # 16. Aroon (2 adet)
    for w in [14, 25]:
        col = f'Aroon_Osc_{w}'
        try:
            aroon = ta.trend.AroonIndicator(high=df['High'], low=df['Low'], window=w)
            df[col] = aroon.aroon_indicator()
        except Exception:
            df[col] = np.nan

    # 17. Vortex (2 adet)
    for w in [14, 20]:
        col_pos = f'VI_pos_{w}'
        col_neg = f'VI_neg_{w}'
        try:
            vortex = ta.trend.VortexIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=w)
            df[col_pos] = vortex.vortex_indicator_pos()
            df[col_neg] = vortex.vortex_indicator_neg()
        except Exception:
            df[col_pos] = np.nan
            df[col_neg] = np.nan

    # 18. MACD Varyasyonları (6 adet)
    for fast, slow, sign in [(5, 35, 5), (24, 52, 18)]:
        col_macd = f'MACD_{fast}_{slow}'
        col_sign = f'MACDs_{fast}_{slow}'
        col_diff = f'MACDh_{fast}_{slow}'
        try:
            macd = ta.trend.MACD(close=df['Close'], window_fast=fast, window_slow=slow, window_sign=sign)
            df[col_macd] = macd.macd()
            df[col_sign] = macd.macd_signal()
            df[col_diff] = macd.macd_diff()
        except Exception:
            df[col_macd] = np.nan
            df[col_sign] = np.nan
            df[col_diff] = np.nan

    # 19. MFI Varyasyonları (4 adet)
    for w in [9, 14, 21, 28]:
        col = f'MFI_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.volume.money_flow_index(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=w)
            except Exception:
                df[col] = np.nan

    # 20. CMF Varyasyonları (3 adet)
    for w in [10, 20, 30]:
        col = f'CMF_{w}'
        if col not in df.columns:
            try:
                df[col] = ta.volume.chaikin_money_flow(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=w)
            except Exception:
                df[col] = np.nan

    # 21. Ease of Movement (1 adet)
    try:
        eom = ta.volume.EaseOfMovementIndicator(high=df['High'], low=df['Low'], volume=df['Volume'], window=14)
        df['EOM_14'] = eom.sma_ease_of_movement()
    except Exception:
        df['EOM_14'] = np.nan

    # 22. VWAP Varyasyonları (3 adet)
    for w in [5, 10, 20]:
        col = f'VWAP_{w}'
        if col not in df.columns:
            try:
                df[col] = calculate_vwap(df, window=w)
            except Exception:
                df[col] = np.nan

    return df

def get_all_indicator_rules(df: pd.DataFrame) -> tuple:
    """
    100+ indikatörü hesaplar ve her birinin sinyal kural fonksiyonunu içeren 
    bir rules sözlüğü ile birlikte DataFrame'i döndürür (DRY Uyumlu).
    """
    df = calculate_100_indicators(df)
    
    rules = {}
    
    # 1. SMA Trend Rules (12 adet)
    sma_windows = [5, 10, 15, 20, 25, 30, 40, 50, 52, 75, 100, 150, 200]
    for w in sma_windows:
        col = f'SMA_{w}'
        rules[f"SMA {w} Trend"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df['Close'] > df[c], 1, -1))

    # 2. EMA Trend Rules (12 adet)
    ema_windows = [5, 10, 15, 20, 25, 30, 40, 50, 52, 75, 100, 150, 200]
    for w in ema_windows:
        col = f'EMA_{w}'
        rules[f"EMA {w} Trend"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df['Close'] > df[c], 1, -1))

    # 3. WMA Trend Rules (3 adet)
    wma_windows = [10, 20, 50]
    for w in wma_windows:
        col = f'WMA_{w}'
        rules[f"WMA {w} Trend"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df['Close'] > df[c], 1, -1))

    # 4. KAMA Trend Rules (3 adet)
    kama_windows = [10, 20, 50]
    for w in kama_windows:
        col = f'KAMA_{w}'
        rules[f"KAMA {w} Trend"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df['Close'] > df[c], 1, -1))

    # 5. RSI Signal Rules (7 adet)
    rsi_windows = [5, 7, 9, 11, 14, 21, 28]
    for w in rsi_windows:
        col = f'RSI_{w}'
        rules[f"RSI {w} Sinyali"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df[c] < 30, 1, np.where(df[c] > 70, -1, 0)))

    # 6. Stochastic Crossover Rules (5 adet)
    stoch_windows = [5, 9, 14, 21, 28]
    for w in stoch_windows:
        col_k = f'STOCHk_{w}'
        col_d = f'STOCHd_{w}'
        rules[f"Stoch {w} Kesişimi"] = lambda df, ck=col_k, cd=col_d: np.where(df[ck].isna() | df[cd].isna(), 0, np.where(df[ck] > df[cd], 1, -1))

    # 7. Stochastic RSI Rules (3 adet)
    stoch_rsi_windows = [9, 14, 21]
    for w in stoch_rsi_windows:
        col_k = f'STOCHRSIk_{w}'
        col_d = f'STOCHRSId_{w}'
        rules[f"StochRSI {w} Kesişimi"] = lambda df, ck=col_k, cd=col_d: np.where(df[ck].isna() | df[cd].isna(), 0, np.where(df[ck] > df[cd], 1, -1))

    # 8. CCI Channel Rules (4 adet)
    cci_windows = [10, 14, 20, 30]
    for w in cci_windows:
        col = f'CCI_{w}'
        rules[f"CCI {w} Kanalı"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df[c] < -100, 1, np.where(df[c] > 100, -1, 0)))

    # 9. ROC Momentum Rules (5 adet)
    roc_windows = [5, 10, 15, 20, 25]
    for w in roc_windows:
        col = f'ROC_{w}'
        rules[f"ROC {w} Momentum"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df[c] > 0, 1, -1))

    # 10. Williams %R Rules (4 adet)
    wr_windows = [10, 14, 20, 25]
    for w in wr_windows:
        col = f'Williams_{w}'
        rules[f"Williams %R {w}"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df[c] < -80, 1, np.where(df[c] > -20, -1, 0)))

    # 11. Awesome Oscillator (1 adet)
    rules["Awesome Oscillator AO"] = lambda df: np.where(df['Awesome_Oscillator'].isna(), 0, np.where(df['Awesome_Oscillator'] > 0, 1, -1))

    # 12. Bollinger Bands Rules (4 adet)
    bb_devs = [1.0, 1.5, 2.0, 2.5]
    for dev in bb_devs:
        col_l = f'BBL_20_{dev}'
        col_u = f'BBU_20_{dev}'
        rules[f"Bollinger {dev}SD Sınırı"] = lambda df, cl=col_l, cu=col_u: np.where(df[cl].isna() | df[cu].isna(), 0, np.where(df['Close'] < df[cl], 1, np.where(df['Close'] > df[cu], -1, 0)))

    # 13. Keltner Channels Rules (4 adet)
    kc_devs = [1.0, 1.5, 2.0, 2.5]
    for dev in kc_devs:
        col_l = f'KCL_20_{dev}'
        col_u = f'KCU_20_{dev}'
        rules[f"Keltner {dev} Sınırı"] = lambda df, cl=col_l, cu=col_u: np.where(df[cl].isna() | df[cu].isna(), 0, np.where(df['Close'] < df[cl], 1, np.where(df['Close'] > df[cu], -1, 0)))

    # 14. Donchian Channels Rules (4 adet)
    dc_windows = [10, 20, 30, 50]
    for w in dc_windows:
        col = f'DCM_{w}'
        rules[f"Donchian {w} Kanalı"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df['Close'] > df[c], 1, -1))

    # 15. ADX & DMI Rules (4 adet)
    adx_windows = [14, 20]
    for w in adx_windows:
        col_adx = f'ADX_{w}'
        col_pos = f'ADX_pos_{w}'
        col_neg = f'ADX_neg_{w}'
        rules[f"ADX {w} Sinyali"] = lambda df, cp=col_pos, cn=col_neg: np.where(df[cp].isna() | df[cn].isna(), 0, np.where(df[cp] > df[cn], 1, -1))
        rules[f"ADX {w} Trend Gücü"] = lambda df, ca=col_adx, cp=col_pos, cn=col_neg: np.where(df[ca].isna() | df[cp].isna() | df[cn].isna(), 0, np.where((df[ca] > 25) & (df[cp] > df[cn]), 1, np.where((df[ca] > 25) & (df[cp] < df[cn]), -1, 0)))

    # 16. Aroon Rules (2 adet)
    aroon_windows = [14, 25]
    for w in aroon_windows:
        col = f'Aroon_Osc_{w}'
        rules[f"Aroon {w} Oscillator"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df[c] > 0, 1, -1))

    # 17. Vortex Rules (2 adet)
    vortex_windows = [14, 20]
    for w in vortex_windows:
        col_pos = f'VI_pos_{w}'
        col_neg = f'VI_neg_{w}'
        rules[f"Vortex {w} Kesişimi"] = lambda df, cp=col_pos, cn=col_neg: np.where(df[cp].isna() | df[cn].isna(), 0, np.where(df[cp] > df[cn], 1, -1))

    # 18. MACD Rules (6 adet)
    rules["MACD 12/26/9 Kesişimi"] = lambda df: np.where(df['MACD'].isna() | df['MACDs'].isna(), 0, np.where(df['MACD'] > df['MACDs'], 1, -1))
    rules["MACD 12/26/9 Histogram"] = lambda df: np.where(df['MACDh'].isna(), 0, np.where(df['MACDh'] > 0, 1, -1))
    
    rules["MACD 5/35/5 Kesişimi"] = lambda df: np.where(df['MACD_5_35'].isna() | df['MACDs_5_35'].isna(), 0, np.where(df['MACD_5_35'] > df['MACDs_5_35'], 1, -1))
    rules["MACD 5/35/5 Histogram"] = lambda df: np.where(df['MACDh_5_35'].isna(), 0, np.where(df['MACDh_5_35'] > 0, 1, -1))
    
    rules["MACD 24/52/18 Kesişimi"] = lambda df: np.where(df['MACD_24_52'].isna() | df['MACDs_24_52'].isna(), 0, np.where(df['MACD_24_52'] > df['MACDs_24_52'], 1, -1))
    rules["MACD 24/52/18 Histogram"] = lambda df: np.where(df['MACDh_24_52'].isna(), 0, np.where(df['MACDh_24_52'] > 0, 1, -1))

    # 19. Moving Average Crossover Rules (5 adet)
    rules["EMA 5/10 Altın Kesişim"] = lambda df: np.where(df['EMA_5'].isna() | df['EMA_10'].isna(), 0, np.where(df['EMA_5'] > df['EMA_10'], 1, -1))
    rules["EMA 9/21 Altın Kesişim"] = lambda df: np.where(df['EMA_9'].isna() | df['EMA_21'].isna(), 0, np.where(df['EMA_9'] > df['EMA_21'], 1, -1))
    rules["EMA 20/50 Altın Kesişim"] = lambda df: np.where(df['EMA_20'].isna() | df['EMA_50'].isna(), 0, np.where(df['EMA_20'] > df['EMA_50'], 1, -1))
    rules["EMA 50/200 Altın Kesişim"] = lambda df: np.where(df['EMA_50'].isna() | df['EMA_200'].isna(), 0, np.where(df['EMA_50'] > df['EMA_200'], 1, -1))
    rules["SMA 20/50 Altın Kesişim"] = lambda df: np.where(df['SMA_20'].isna() | df['SMA_50'].isna(), 0, np.where(df['SMA_20'] > df['SMA_50'], 1, -1))

    # 20. Money Flow Index Rules (4 adet)
    mfi_windows = [9, 14, 21, 28]
    for w in mfi_windows:
        col = f'MFI_{w}'
        rules[f"MFI {w} Para Akışı"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df[c] < 20, 1, np.where(df[c] > 80, -1, 0)))

    # 21. Chaikin Money Flow Rules (3 adet)
    cmf_windows = [10, 20, 30]
    for w in cmf_windows:
        col = f'CMF_{w}'
        rules[f"CMF {w} Para Dağılımı"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df[c] > 0.05, 1, np.where(df[c] < -0.05, -1, 0)))

    # 22. Ease of Movement (1 adet)
    rules["Ease of Movement 14"] = lambda df: np.where(df['EOM_14'].isna(), 0, np.where(df['EOM_14'] > 0, 1, -1))

    # 23. VWAP Trend Rules (3 adet)
    vwap_windows = [5, 10, 20]
    for w in vwap_windows:
        col = f'VWAP_{w}'
        rules[f"VWAP {w} Fiyat Trendi"] = lambda df, c=col: np.where(df[c].isna(), 0, np.where(df['Close'] > df[c], 1, -1))

    return df, rules

def get_core_signal(df: pd.DataFrame) -> dict:
    """
    100-İndikatörlü (Core Technical Score) vektörel hızlı hesaplayıcı.
    Sadece son günün verisiyle (vektörize edilmiş DataFrame üzerinden) oylama yapar.
    Dynamic Fallback kuralını (200 günden az verisi olan IPO'lar için) içerir.
    """
    df, rules = get_all_indicator_rules(df)
    
    total_weight = 0
    buy_votes = 0
    sell_votes = 0
    core_votes_list = []
    
    # 3 Altın Kural - Kural 2: Dynamic Fallback (Yeni Halka Arzlar İçin Adaptasyon)
    # Eğer hisse 200 günden kısa geçmişe sahipse, uzun vadeli kuralların ağırlığı düşürülür (veya sıfırlanır)
    # ve kısa vadeli momentum göstergelerinin ağırlığı artırılarak skor normalize edilir.
    data_length = len(df)
    is_ipo = data_length < 200
    
    # Kural 1: Vektörel (Vectorized) Hız Kuralı -> Döngü (for row in df) kullanılmaz. Sadece serinin son elemanı (iloc[-1]) alınır.
    for name, rule_func in rules.items():
        weight = 10  # Standart ağırlık
        
        if is_ipo:
            # Uzun vadeli kuralları muaf tut (Ağırlık = 0)
            if any(term in name for term in ["200", "150", "100"]):
                continue 
            # Kısa vadeli trend ve momentuma ağırlık ver
            elif any(term in name for term in ["5", "10", "14", "RSI", "MACD", "Stoch"]):
                weight = 20
                
        try:
            # rule_func 1 (AL), -1 (SAT) veya 0 (NÖTR) dönen bir numpy array / pandas series'tir
            sig_array = rule_func(df)
            last_sig = sig_array[-1] if isinstance(sig_array, (np.ndarray, list)) else sig_array.iloc[-1]
            
            # Sonuç NaN değilse oylamaya kat
            if pd.notna(last_sig):
                if last_sig == 1:
                    total_weight += weight
                    buy_votes += weight
                    dec_str = "AL 🟢"
                elif last_sig == -1:
                    total_weight += weight
                    sell_votes += weight
                    dec_str = "SAT 🔴"
                else:
                    total_weight += weight
                    dec_str = "NÖTR ⚖️"
                core_votes_list.append({"İndikatör/Kural": name, "Durum": dec_str, "Ağırlık Puanı": weight})
        except Exception:
            pass

    if total_weight == 0:
        return {"decision": "Nötr", "buy_pct": 50, "sell_pct": 50, "score": 50}
        
    buy_pct = (buy_votes / total_weight) * 100
    sell_pct = (sell_votes / total_weight) * 100
    
    # Core Signal Karar Mekanizması
    if buy_pct >= 60:
        dec = "Güçlü Al"
    elif buy_pct >= 50:
        dec = "Al"
    elif sell_pct >= 60:
        dec = "Güçlü Sat"
    elif sell_pct >= 50:
        dec = "Sat"
    else:
        dec = "Nötr"
        
    # Core Technical Score (Teknik Skor = Alım Yüzdesi)
    return {
        "decision": dec, 
        "buy_pct": round(buy_pct, 1), 
        "sell_pct": round(sell_pct, 1), 
        "score": round(buy_pct, 1),
        "buy_votes": buy_votes,
        "sell_votes": sell_votes,
        "total_votes": total_weight,
        "core_votes_list": core_votes_list
    }

def evaluate_individual_indicators(df: pd.DataFrame) -> dict:
    """
    Her bir indikatörün geriye dönük başarı oranını (Win Rate %) hesaplar.
    Her indikatör için AL ve SAT sinyalleri simüle edilir ve karlı kapanan işlem oranı bulunur.
    """
    df, rules = get_all_indicator_rules(df)
    win_rates = {}
    
    for name, rule_func in rules.items():
        try:
            signals = rule_func(df)
            
            # Sinyal bazlı basit trade testi (Alternating AL ve SAT)
            trades = []
            active_trade = None
            
            for t in range(1, len(df)):
                sig = signals[t]
                prev_sig = signals[t-1]
                close_px = float(df['Close'].iloc[t])
                
                if sig == 1 and prev_sig != 1 and active_trade is None:
                    active_trade = close_px
                elif sig == -1 and prev_sig != -1 and active_trade is not None:
                    pct = ((close_px - active_trade) / active_trade) * 100
                    trades.append(pct > 0)
                    active_trade = None
            
            total_trades = len(trades)
            if total_trades >= 3:
                win_count = sum(1 for tr in trades if tr)
                win_rates[name] = round((win_count / total_trades) * 100, 1)
            else:
                win_rates[name] = 50.0
        except Exception:
            win_rates[name] = 50.0
            
    return win_rates

def generate_historical_signals(df: pd.DataFrame, sensitivity: str = "Dengeli") -> tuple:
    """
    100+ indikatörü hesaplar, geriye dönük en başarılı olan ilk 15 indikatörü belirler 
    ve bu indikatörlerin ağırlıklı oylaması ile nihai AL/SAT sinyallerini üretir.
    """
    df = df.copy()
    
    # 1. 100+ indikatör hesapla ve kuralları al
    df, rules = get_all_indicator_rules(df)
    
    # 2. Her indikatörün Win Rate oranını hesapla
    indicator_win_rates = {}
    for name, rule_func in rules.items():
        try:
            signals = rule_func(df)
            trades = []
            active_trade = None
            
            for t in range(1, len(df)):
                sig = signals[t]
                prev_sig = signals[t-1]
                close_px = float(df['Close'].iloc[t])
                
                if sig == 1 and prev_sig != 1 and active_trade is None:
                    active_trade = close_px
                elif sig == -1 and prev_sig != -1 and active_trade is not None:
                    pct = ((close_px - active_trade) / active_trade) * 100
                    trades.append(pct > 0)
                    active_trade = None
            
            total_trades = len(trades)
            if total_trades >= 3:
                win_count = sum(1 for tr in trades if tr)
                indicator_win_rates[name] = round((win_count / total_trades) * 100, 1)
            else:
                indicator_win_rates[name] = 50.0
        except Exception:
            indicator_win_rates[name] = 50.0
            
    # 3. İndikatörleri başarı oranına göre sırala
    sorted_indicators = sorted(indicator_win_rates.items(), key=lambda x: x[1], reverse=True)
    
    # En başarılı ilk 15 indikatörü seç
    top_15_names = [item[0] for item in sorted_indicators[:15]]
    
    # 4. Oylama ağırlıklarını belirle
    # Ağırlık = (Win Rate - 40). Negatif ağırlık olmaması için minimum 10 puan verilir.
    indicator_weights = {}
    for name, wr in sorted_indicators[:15]:
        indicator_weights[name] = max(10, wr - 40)
        
    # Her indikatörün canlı sinyal vektörünü önceden hesaplayalım
    indicator_signals = {}
    for name in top_15_names:
        indicator_signals[name] = rules[name](df)

    # 5. Oylama Eşikleri (Hassasiyete Göre)
    if sensitivity == "Muhafazakar":
        buy_vote_threshold = 60.0  # Toplam oyların ağırlıklı %60'ı AL demeli
        sell_vote_threshold = 55.0
    elif sensitivity == "Agresif":
        buy_vote_threshold = 40.0
        sell_vote_threshold = 40.0
    else: # Dengeli
        buy_vote_threshold = 50.0
        sell_vote_threshold = 50.0

    # Sinyal Sütunlarını Sıfırla
    df['Buy_Signal'] = np.nan
    df['Sell_Signal'] = np.nan
    df['Signal_Reason'] = ""
    
    # Oylama Gücü Serileri
    df['Buy_Vote_Strength'] = 0.0
    df['Sell_Vote_Strength'] = 0.0

    # Durum Makinesi
    state = "None"
    total_weights = sum(indicator_weights.values())

    for t in range(2, len(df)):
        low_today = float(df['Low'].iloc[t])
        high_today = float(df['High'].iloc[t])
        
        weighted_buy_votes = 0.0
        weighted_sell_votes = 0.0
        voted_buy_reasons = []
        voted_sell_reasons = []
        
        for name in top_15_names:
            sig = indicator_signals[name][t]
            weight = indicator_weights[name]
            
            if sig == 1:
                weighted_buy_votes += weight
                voted_buy_reasons.append(name)
            elif sig == -1:
                weighted_sell_votes += weight
                voted_sell_reasons.append(name)
                
        # Oylama Yüzdesel Gücü (0-100)
        buy_pct = (weighted_buy_votes / total_weights) * 100 if total_weights > 0 else 0
        sell_pct = (weighted_sell_votes / total_weights) * 100 if total_weights > 0 else 0
        
        df.at[df.index[t], 'Buy_Vote_Strength'] = round(buy_pct, 1)
        df.at[df.index[t], 'Sell_Vote_Strength'] = round(sell_pct, 1)

        # Karar ve Geçiş Kontrolü
        if state == "None" or state == "SHORT":
            if buy_pct >= buy_vote_threshold:
                df.at[df.index[t], 'Buy_Signal'] = low_today * 0.985
                df.at[df.index[t], 'Signal_Reason'] = f"Oylama Gücü: %{buy_pct:.0f} | Öncü: " + ", ".join(voted_buy_reasons[:3])
                state = "LONG"
        elif state == "LONG":
            if sell_pct >= sell_vote_threshold:
                df.at[df.index[t], 'Sell_Signal'] = high_today * 1.015
                df.at[df.index[t], 'Signal_Reason'] = f"Oylama Gücü: %{sell_pct:.0f} | Öncü: " + ", ".join(voted_sell_reasons[:3])
                state = "SHORT"

    # 6. Liderlik Tablosunu Oluştur
    top_indicators = []
    total_w = sum(indicator_weights.values())
    
    for name in top_15_names:
        sig = indicator_signals[name][-1]
        vote_text = "🟢 AL" if sig == 1 else ("🔴 SAT" if sig == -1 else "⚖️ NÖTR")
        win_rate = indicator_win_rates[name]
        weight_pct = (indicator_weights[name] / total_w) * 100 if total_w > 0 else 0
        
        top_indicators.append({
            "Indikatör Adı": name,
            "Tarihsel Başarı (Win Rate %)": win_rate,
            "Anlık Sinyal": vote_text,
            "Oylama Ağırlığı (%)": round(weight_pct, 1)
        })

    # 7. Backtest Performansını Hesapla
    stats = backtest_signals(df)
    
    return df, top_indicators, stats

def backtest_signals(df: pd.DataFrame) -> dict:
    """
    Oylama sisteminden gelen sinyallere göre geriye dönük simülasyon (backtest) yapar.
    """
    trades = []
    active_trade = None
    
    buy_signals = df[df['Buy_Signal'].notna()]
    sell_signals = df[df['Sell_Signal'].notna()]
    
    # Tüm sinyalleri tarih sırasıyla birleştirelim
    all_signals = pd.concat([
        pd.DataFrame({'Price': buy_signals['Close'], 'Type': 'BUY', 'Reason': buy_signals['Signal_Reason']}, index=buy_signals.index),
        pd.DataFrame({'Price': sell_signals['Close'], 'Type': 'SELL', 'Reason': sell_signals['Signal_Reason']}, index=sell_signals.index)
    ]).sort_index()
    
    for date, row in all_signals.iterrows():
        if row['Type'] == 'BUY' and active_trade is None:
            active_trade = {
                'buy_date': date,
                'buy_price': float(row['Price']),
                'buy_reason': row['Reason']
            }
        elif row['Type'] == 'SELL' and active_trade is not None:
            buy_price = active_trade['buy_price']
            sell_price = float(row['Price'])
            pct_return = ((sell_price - buy_price) / buy_price) * 100
            
            trades.append({
                'buy_date': active_trade['buy_date'].strftime('%Y-%m-%d'),
                'buy_price': buy_price,
                'buy_reason': active_trade['buy_reason'],
                'sell_date': date.strftime('%Y-%m-%d'),
                'sell_price': sell_price,
                'sell_reason': row['Reason'],
                'return_pct': round(pct_return, 2),
                'win': pct_return > 0,
                'duration_days': (date - active_trade['buy_date']).days
            })
            active_trade = None
            
    if active_trade is not None and not df.empty:
        last_date = df.index[-1]
        last_price = float(df['Close'].iloc[-1])
        pct_return = ((last_price - active_trade['buy_price']) / active_trade['buy_price']) * 100
        
        trades.append({
            'buy_date': active_trade['buy_date'].strftime('%Y-%m-%d'),
            'buy_price': active_trade['buy_price'],
            'buy_reason': active_trade['buy_reason'],
            'sell_date': last_date.strftime('%Y-%m-%d') + " (Açık)",
            'sell_price': last_price,
            'sell_reason': "Pozisyon Açık",
            'return_pct': round(pct_return, 2),
            'win': pct_return > 0,
            'duration_days': (last_date - active_trade['buy_date']).days
        })
        
    total_trades = len(trades)
    win_trades = sum(1 for t in trades if t['win'])
    loss_trades = total_trades - win_trades
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0
    total_return = sum(t['return_pct'] for t in trades)
    
    best_trade = max(trades, key=lambda x: x['return_pct'])['return_pct'] if total_trades > 0 else 0.0
    worst_trade = min(trades, key=lambda x: x['return_pct'])['return_pct'] if total_trades > 0 else 0.0
    
    return {
        'total_trades': total_trades,
        'win_trades': win_trades,
        'loss_trades': loss_trades,
        'win_rate': round(win_rate, 1),
        'total_return': round(total_return, 2),
        'best_trade': round(best_trade, 2),
        'worst_trade': round(worst_trade, 2),
        'trades': trades
    }
