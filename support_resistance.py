import pandas as pd
import numpy as np

def calculate_pivot_points(df: pd.DataFrame) -> dict:
    """
    Klasik Pivot Noktaları (Floor Pivot) hesaplar.
    Son kapanış barına göre: PP, R1, R2, R3, S1, S2, S3
    """
    if df.empty or len(df) < 2:
        return {}

    # Son tamamlanmış bar'ın verileri
    last = df.iloc[-1]
    H = last['High']
    L = last['Low']
    C = last['Close']

    PP = (H + L + C) / 3
    R1 = (2 * PP) - L
    S1 = (2 * PP) - H
    R2 = PP + (H - L)
    S2 = PP - (H - L)
    R3 = H + 2 * (PP - L)
    S3 = L - 2 * (H - PP)

    return {
        'PP': round(PP, 2),
        'R1': round(R1, 2), 'R2': round(R2, 2), 'R3': round(R3, 2),
        'S1': round(S1, 2), 'S2': round(S2, 2), 'S3': round(S3, 2)
    }


def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Son `lookback` bar içindeki en yüksek ve en düşük fiyatları bularak
    Fibonacci Retracement seviyelerini hesaplar.
    """
    if df.empty or len(df) < lookback:
        lookback = len(df)

    recent = df.tail(lookback)
    high = recent['High'].max()
    low = recent['Low'].min()
    diff = high - low

    levels = {
        'Zirve (1.0)': round(high, 2),
        'Fib 0.786': round(high - diff * 0.214, 2),
        'Fib 0.618': round(high - diff * 0.382, 2),
        'Fib 0.500': round(high - diff * 0.500, 2),
        'Fib 0.382': round(high - diff * 0.618, 2),
        'Fib 0.236': round(high - diff * 0.764, 2),
        'Dip (0.0)': round(low, 2),
    }
    return levels


def find_swing_levels(df: pd.DataFrame, window: int = 10, count: int = 5) -> dict:
    """
    Swing High ve Swing Low noktalarını bularak en güçlü destek ve direnç
    bölgelerini tespit eder. `window` parametresi kaç barlık pencerede
    tepe/dip aranacağını belirler.
    """
    if df.empty or len(df) < window * 2:
        return {'supports': [], 'resistances': []}

    highs = df['High'].values
    lows = df['Low'].values

    swing_highs = []
    swing_lows = []

    for i in range(window, len(df) - window):
        # Swing High: Ortadaki bar, penceredeki en yüksek
        if highs[i] == max(highs[i - window: i + window + 1]):
            swing_highs.append(round(highs[i], 2))
        # Swing Low: Ortadaki bar, penceredeki en düşük
        if lows[i] == min(lows[i - window: i + window + 1]):
            swing_lows.append(round(lows[i], 2))

    # Kümeleme: Birbirine çok yakın (<%2 fark) seviyeleri birleştir
    def cluster_levels(levels, threshold_pct=0.02):
        if not levels:
            return []
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]
        for i in range(1, len(levels)):
            if (levels[i] - current_cluster[0]) / current_cluster[0] < threshold_pct:
                current_cluster.append(levels[i])
            else:
                clusters.append(round(np.mean(current_cluster), 2))
                current_cluster = [levels[i]]
        clusters.append(round(np.mean(current_cluster), 2))
        return clusters

    clustered_supports = cluster_levels(swing_lows)
    clustered_resistances = cluster_levels(swing_highs)

    # En son fiyata en yakın olanları seç
    close_price = df['Close'].iloc[-1]

    # Destekler: fiyatın altındakiler (en yakından uzağa)
    supports = sorted([s for s in clustered_supports if s < close_price], reverse=True)[:count]
    # Dirençler: fiyatın üstündekiler (en yakından uzağa)
    resistances = sorted([r for r in clustered_resistances if r > close_price])[:count]

    return {'supports': supports, 'resistances': resistances}


def calculate_best_zones(df: pd.DataFrame) -> dict:
    """
    Tüm hesaplamaları birleştirerek 'En İyi Alım Bölgesi' ve
    'En İyi Satım Bölgesi' önerileri üretir.
    """
    if df.empty or len(df) < 20:
        return {}

    close_price = df['Close'].iloc[-1]
    pivots = calculate_pivot_points(df)
    fibs = calculate_fibonacci_levels(df)
    swings = find_swing_levels(df)

    # --- EN İYİ ALIM BÖLGESİ ---
    # Fiyatın altındaki en güçlü destek noktalarını topla
    buy_candidates = []

    if pivots.get('S1') and pivots['S1'] < close_price:
        buy_candidates.append(('Pivot S1', pivots['S1']))
    if pivots.get('S2') and pivots['S2'] < close_price:
        buy_candidates.append(('Pivot S2', pivots['S2']))

    for name, val in fibs.items():
        if val < close_price and 'Fib' in name:
            buy_candidates.append((name, val))

    for s in swings.get('supports', [])[:3]:
        buy_candidates.append(('Swing Destek', s))

    # En yakın destek = en güvenli alım noktası
    buy_candidates.sort(key=lambda x: x[1], reverse=True)

    # --- EN İYİ SATIM BÖLGESİ ---
    sell_candidates = []

    if pivots.get('R1') and pivots['R1'] > close_price:
        sell_candidates.append(('Pivot R1', pivots['R1']))
    if pivots.get('R2') and pivots['R2'] > close_price:
        sell_candidates.append(('Pivot R2', pivots['R2']))

    for name, val in fibs.items():
        if val > close_price and 'Fib' in name:
            sell_candidates.append((name, val))

    for r in swings.get('resistances', [])[:3]:
        sell_candidates.append(('Swing Direnç', r))

    sell_candidates.sort(key=lambda x: x[1])

    return {
        'close_price': round(close_price, 2),
        'pivots': pivots,
        'fibonacci': fibs,
        'swings': swings,
        'best_buy_zones': buy_candidates[:5],   # En iyi 5 alım noktası
        'best_sell_zones': sell_candidates[:5],  # En iyi 5 satım noktası
    }
