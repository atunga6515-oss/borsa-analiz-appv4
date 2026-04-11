import pandas as pd
import numpy as np

def detect_candlestick_patterns(df: pd.DataFrame) -> dict:
    """
    DataFrame içindeki son 'window' kadarki mumları inceleyip,
    özel mum formasyonlarını tespit eder.
    Sinyalleri son 3 gün içindekileri önceliklendirerek raporlar.
    """
    if df.empty or len(df) < 5:
        return {}

    patterns_detected = []
    
    # Sadece son 3 günün analizini yap
    recent_df = df.tail(3).copy()
    
    for i in range(len(recent_df)):
        idx = recent_df.index[i]
        date_str = str(idx.date()) if hasattr(idx, 'date') else str(idx)
        
        row = recent_df.iloc[i]
        
        # O, H, L, C
        O = row['Open']
        H = row['High']
        L = row['Low']
        C = row['Close']
        
        body = abs(C - O)
        upper_shadow = H - max(O, C)
        lower_shadow = min(O, C) - L
        
        is_bullish = C > O
        is_bearish = C < O
        
        body_percent = body / (O + 0.0001) * 100
        
        # 1. Doji (Vücut çok küçük)
        if body_percent < 0.1:
            patterns_detected.append(f"{date_str} - Kararsızlık Mumu (Doji)")
            
        # 2. Çekiç (Hammer) - Alt gölge çok uzun, üst gölge kısa, küçük - orta vücut
        if is_bullish and lower_shadow > (2 * body) and upper_shadow < (0.2 * body):
            patterns_detected.append(f"{date_str} - Boğa Yükseliş Sinyali: Çekiç (Hammer)")
            
        # Kayan Yıldız (Shooting Star) - Üst gölge çok uzun, alt gölge kısa
        if is_bearish and upper_shadow > (2 * body) and lower_shadow < (0.2 * body):
            patterns_detected.append(f"{date_str} - Ayı Düşüş Sinyali: Kayan Yıldız (Shooting Star)")

        # Engulfing (Yutan Boğa/Ayı) check requires previous day
        if i > 0:
            prev_row = recent_df.iloc[i-1]
            prev_O, prev_C = prev_row['Open'], prev_row['Close']
            prev_is_bullish = prev_C > prev_O
            prev_is_bearish = prev_C < prev_O
            
            # Yutan Boğa (Bullish Engulfing)
            if prev_is_bearish and is_bullish:
                if O < prev_C and C > prev_O:
                    patterns_detected.append(f"{date_str} - Güçlü Boğa Sinyali: Yutan Küme (Bullish Engulfing)")
                    
            # Yutan Ayı (Bearish Engulfing)
            if prev_is_bullish and is_bearish:
                if O > prev_C and C < prev_O:
                    patterns_detected.append(f"{date_str} - Güçlü Ayı Sinyali: Yutan Satış (Bearish Engulfing)")

    # Sadece en güncel patternları dön veya summary olarak birleştir
    result = {}
    if patterns_detected:
        result['summary'] = "\n".join(patterns_detected)
    else:
        result['summary'] = "Son günlerde belirgin bir mum formasyonu tespit edilmedi."
        
    return result
