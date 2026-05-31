"""
Strateji Karşılaştırma Motoru — v3.0.0
5 farklı trading stratejisini aynı hisse üzerinde backtest eder ve karşılaştırır.
Sharpe Ratio, Sortino Ratio, Win Rate, Max Drawdown, Profit Factor metrikleri hesaplanır.
"""
import pandas as pd
import numpy as np
import ta
from indicators import calculate_indicators
from signals_engine import generate_historical_signals


# ============================================================
# STRATEJİ TANIMLARI
# ============================================================

STRATEGY_NAMES = {
    "momentum": "📈 Momentum (Trend Following)",
    "mean_reversion": "🔄 Mean Reversion (Ortalamaya Dönüş)",
    "breakout": "🚀 Breakout (Kırılım)",
    "macd_crossover": "📊 MACD Crossover",
    "ensemble_101": "🤖 Ensemble (101 İndikatör Oylama)"
}


def _calculate_metrics(trades: list, equity_curve: pd.Series, initial_capital: float) -> dict:
    """
    İşlem listesi ve equity eğrisinden tüm performans metriklerini hesaplar.
    
    Returns:
        dict: Tüm performans metrikleri
    """
    if not trades or equity_curve is None or len(equity_curve) < 2:
        return {
            'total_return_pct': 0, 'sharpe_ratio': 0, 'sortino_ratio': 0,
            'win_rate': 0, 'max_drawdown_pct': 0, 'total_trades': 0,
            'avg_trade_duration': 0, 'profit_factor': 0,
            'best_trade_pct': 0, 'worst_trade_pct': 0
        }
    
    # Getiri hesapla
    returns = equity_curve.pct_change().dropna()
    total_return = ((equity_curve.iloc[-1] - initial_capital) / initial_capital) * 100
    
    # Sharpe Ratio (Risk-free rate ≈ %15 TL — Türkiye faiz oranı, günlüğe çevir)
    risk_free_daily = (1.15 ** (1/252)) - 1
    excess_returns = returns - risk_free_daily
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0
    
    # Sortino Ratio (Sadece negatif volatiliteyi hesaplar)
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
    sortino = (excess_returns.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0
    
    # Max Drawdown
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    max_dd = abs(drawdown.min()) * 100
    
    # İşlem Bazlı Metrikler
    completed_trades = [t for t in trades if t.get('return_pct') is not None]
    win_trades = [t for t in completed_trades if t.get('return_pct', 0) > 0]
    loss_trades = [t for t in completed_trades if t.get('return_pct', 0) <= 0]
    
    total_count = len(completed_trades)
    win_rate = (len(win_trades) / total_count * 100) if total_count > 0 else 0
    
    # Profit Factor = Toplam Kazanç / Toplam Kayıp
    total_gains = sum(t['return_pct'] for t in win_trades) if win_trades else 0
    total_losses = abs(sum(t['return_pct'] for t in loss_trades)) if loss_trades else 0
    profit_factor = (total_gains / total_losses) if total_losses > 0 else (total_gains if total_gains > 0 else 0)
    
    # Ortalama işlem süresi
    durations = [t.get('duration_days', 0) for t in completed_trades if t.get('duration_days')]
    avg_duration = np.mean(durations) if durations else 0
    
    # En iyi / en kötü işlem
    trade_returns = [t.get('return_pct', 0) for t in completed_trades]
    best = max(trade_returns) if trade_returns else 0
    worst = min(trade_returns) if trade_returns else 0
    
    return {
        'total_return_pct': round(total_return, 2),
        'sharpe_ratio': round(sharpe, 2),
        'sortino_ratio': round(sortino, 2),
        'win_rate': round(win_rate, 1),
        'max_drawdown_pct': round(max_dd, 2),
        'total_trades': total_count,
        'avg_trade_duration': round(avg_duration, 1),
        'profit_factor': round(profit_factor, 2),
        'best_trade_pct': round(best, 2),
        'worst_trade_pct': round(worst, 2)
    }


# ============================================================
# STRATEJİ 1: MOMENTUM (TREND FOLLOWING)
# ============================================================

def _run_momentum(df: pd.DataFrame, initial_capital: float = 100000.0, commission: float = 0.002) -> dict:
    """
    Momentum stratejisi: SMA 20/50 kesişimi + RSI > 50 + ADX > 25
    AL: SMA20 > SMA50 VE RSI > 50 VE ADX > 25
    SAT: SMA20 < SMA50 VEYA RSI < 40
    """
    df = calculate_indicators(df.copy())
    
    capital = initial_capital
    position = 0
    trades = []
    equity = []
    entry_date = None
    entry_price = 0
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        price = float(row['Close'])
        date = df.index[i]
        
        sma20 = float(row.get('SMA_20', np.nan))
        sma50 = float(row.get('SMA_50', np.nan))
        rsi = float(row.get('RSI_14', 50))
        adx = float(row.get('ADX', 0))
        
        if np.isnan(sma20) or np.isnan(sma50):
            equity.append(capital + position * price)
            continue
        
        # AL sinyali
        if position == 0 and sma20 > sma50 and rsi > 50 and adx > 25:
            position = capital / price
            cost = capital * commission
            capital = -cost
            entry_date = date
            entry_price = price
        
        # SAT sinyali
        elif position > 0 and (sma20 < sma50 or rsi < 40):
            gross = position * price
            cost = gross * commission
            capital = capital + gross - cost
            ret_pct = ((price - entry_price) / entry_price) * 100
            duration = (date - entry_date).days if entry_date else 0
            trades.append({
                'buy_date': str(entry_date)[:10], 'sell_date': str(date)[:10],
                'buy_price': entry_price, 'sell_price': price,
                'return_pct': round(ret_pct, 2), 'duration_days': duration
            })
            position = 0
        
        equity.append(capital + position * price)
    
    # Açık pozisyonu kapat
    if position > 0:
        last_price = float(df['Close'].iloc[-1])
        capital += position * last_price
        position = 0
    
    eq_series = pd.Series(equity, index=df.index[50:50+len(equity)])
    return _calculate_metrics(trades, eq_series, initial_capital)


# ============================================================
# STRATEJİ 2: MEAN REVERSION (ORTALAMAYA DÖNÜŞ)
# ============================================================

def _run_mean_reversion(df: pd.DataFrame, initial_capital: float = 100000.0, commission: float = 0.002) -> dict:
    """
    Mean Reversion stratejisi: RSI + Bollinger Band
    AL: RSI < 30 VE Fiyat alt Bollinger Band'ın altında
    SAT: RSI > 70 VEYA Fiyat üst Bollinger Band'ın üzerinde
    """
    df = calculate_indicators(df.copy())
    
    # Bollinger Bands hesapla
    bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_mid'] = bb.bollinger_mavg()
    
    capital = initial_capital
    position = 0
    trades = []
    equity = []
    entry_date = None
    entry_price = 0
    
    for i in range(25, len(df)):
        row = df.iloc[i]
        price = float(row['Close'])
        date = df.index[i]
        
        rsi = float(row.get('RSI_14', 50))
        bb_lower = float(row.get('BB_lower', np.nan))
        bb_upper = float(row.get('BB_upper', np.nan))
        
        if np.isnan(bb_lower) or np.isnan(bb_upper):
            equity.append(capital + position * price)
            continue
        
        # AL: Aşırı satım + Alt banda dokunuş
        if position == 0 and rsi < 30 and price <= bb_lower:
            position = capital / price
            cost = capital * commission
            capital = -cost
            entry_date = date
            entry_price = price
        
        # SAT: Aşırı alım veya üst banda dokunuş
        elif position > 0 and (rsi > 70 or price >= bb_upper):
            gross = position * price
            cost = gross * commission
            capital = capital + gross - cost
            ret_pct = ((price - entry_price) / entry_price) * 100
            duration = (date - entry_date).days if entry_date else 0
            trades.append({
                'buy_date': str(entry_date)[:10], 'sell_date': str(date)[:10],
                'buy_price': entry_price, 'sell_price': price,
                'return_pct': round(ret_pct, 2), 'duration_days': duration
            })
            position = 0
        
        equity.append(capital + position * price)
    
    if position > 0:
        capital += position * float(df['Close'].iloc[-1])
        position = 0
    
    eq_series = pd.Series(equity, index=df.index[25:25+len(equity)])
    return _calculate_metrics(trades, eq_series, initial_capital)


# ============================================================
# STRATEJİ 3: BREAKOUT (KIRILIM)
# ============================================================

def _run_breakout(df: pd.DataFrame, initial_capital: float = 100000.0, commission: float = 0.002) -> dict:
    """
    Breakout stratejisi: Donchian Channel kırılımı + hacim teyidi
    AL: Fiyat son 20 günlük zirveyi kırdı VE hacim ortalamanın 1.5x üzerinde
    SAT: Fiyat son 20 günlük dibi kırdı VEYA ATR trailing stop
    """
    df = calculate_indicators(df.copy())
    
    # Donchian Channels
    df['DC_high'] = df['High'].rolling(window=20).max()
    df['DC_low'] = df['Low'].rolling(window=20).min()
    df['Vol_avg'] = df['Volume'].rolling(window=20).mean()
    
    # ATR for trailing stop
    atr_indicator = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    df['ATR'] = atr_indicator.average_true_range()
    
    capital = initial_capital
    position = 0
    trades = []
    equity = []
    entry_date = None
    entry_price = 0
    trailing_stop = 0
    
    for i in range(25, len(df)):
        row = df.iloc[i]
        price = float(row['Close'])
        date = df.index[i]
        
        dc_high = float(row.get('DC_high', np.nan))
        dc_low = float(row.get('DC_low', np.nan))
        vol = float(row.get('Volume', 0))
        vol_avg = float(row.get('Vol_avg', 1))
        atr = float(row.get('ATR', 0))
        
        if np.isnan(dc_high) or np.isnan(dc_low):
            equity.append(capital + position * price)
            continue
        
        # Trailing stop güncelle
        if position > 0 and atr > 0:
            new_stop = price - (2.0 * atr)
            trailing_stop = max(trailing_stop, new_stop)
        
        # AL: Zirve kırılımı + hacim teyidi
        if position == 0 and price > dc_high and vol_avg > 0 and vol >= vol_avg * 1.5:
            position = capital / price
            cost = capital * commission
            capital = -cost
            entry_date = date
            entry_price = price
            trailing_stop = price - (2.0 * atr) if atr > 0 else price * 0.95
        
        # SAT: Trailing stop veya dip kırılımı
        elif position > 0 and (price <= trailing_stop or price < dc_low):
            gross = position * price
            cost = gross * commission
            capital = capital + gross - cost
            ret_pct = ((price - entry_price) / entry_price) * 100
            duration = (date - entry_date).days if entry_date else 0
            trades.append({
                'buy_date': str(entry_date)[:10], 'sell_date': str(date)[:10],
                'buy_price': entry_price, 'sell_price': price,
                'return_pct': round(ret_pct, 2), 'duration_days': duration
            })
            position = 0
            trailing_stop = 0
        
        equity.append(capital + position * price)
    
    if position > 0:
        capital += position * float(df['Close'].iloc[-1])
        position = 0
    
    eq_series = pd.Series(equity, index=df.index[25:25+len(equity)])
    return _calculate_metrics(trades, eq_series, initial_capital)


# ============================================================
# STRATEJİ 4: MACD CROSSOVER
# ============================================================

def _run_macd_crossover(df: pd.DataFrame, initial_capital: float = 100000.0, commission: float = 0.002) -> dict:
    """
    MACD Crossover stratejisi: MACD sinyal çizgisi kesişimi + histogram yön değişimi
    AL: MACD > Signal VE Histogram pozitife döndü
    SAT: MACD < Signal VE Histogram negatife döndü
    """
    df = calculate_indicators(df.copy())
    
    macd = ta.trend.MACD(close=df['Close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD_line'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff()
    
    capital = initial_capital
    position = 0
    trades = []
    equity = []
    entry_date = None
    entry_price = 0
    
    for i in range(30, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        price = float(row['Close'])
        date = df.index[i]
        
        macd_line = float(row.get('MACD_line', 0))
        macd_signal = float(row.get('MACD_signal', 0))
        macd_hist = float(row.get('MACD_hist', 0))
        prev_hist = float(prev_row.get('MACD_hist', 0))
        
        # AL: MACD kesişimi + histogram pozitife geçiş
        if position == 0 and macd_line > macd_signal and prev_hist <= 0 and macd_hist > 0:
            position = capital / price
            cost = capital * commission
            capital = -cost
            entry_date = date
            entry_price = price
        
        # SAT: MACD ters kesişimi + histogram negatife geçiş
        elif position > 0 and macd_line < macd_signal and prev_hist >= 0 and macd_hist < 0:
            gross = position * price
            cost = gross * commission
            capital = capital + gross - cost
            ret_pct = ((price - entry_price) / entry_price) * 100
            duration = (date - entry_date).days if entry_date else 0
            trades.append({
                'buy_date': str(entry_date)[:10], 'sell_date': str(date)[:10],
                'buy_price': entry_price, 'sell_price': price,
                'return_pct': round(ret_pct, 2), 'duration_days': duration
            })
            position = 0
        
        equity.append(capital + position * price)
    
    if position > 0:
        capital += position * float(df['Close'].iloc[-1])
        position = 0
    
    eq_series = pd.Series(equity, index=df.index[30:30+len(equity)])
    return _calculate_metrics(trades, eq_series, initial_capital)


# ============================================================
# STRATEJİ 5: ENSEMBLE (101 İNDİKATÖR OYLAMA)
# ============================================================

def _run_ensemble_101(df: pd.DataFrame, initial_capital: float = 100000.0, commission: float = 0.002) -> dict:
    """
    Mevcut 101 indikatörlü oylama sistemi ile backtest.
    """
    df_signals, top_indicators, stats = generate_historical_signals(df.copy(), "Dengeli")
    
    # stats zaten trades listesi içeriyor
    if stats['total_trades'] == 0:
        return _calculate_metrics([], pd.Series([initial_capital]), initial_capital)
    
    # Equity curve oluştur
    capital = initial_capital
    position = 0
    equity = []
    trades_out = []
    
    for i in range(len(df_signals)):
        row = df_signals.iloc[i]
        price = float(row['Close'])
        date = df_signals.index[i]
        
        if pd.notna(row.get('Buy_Signal')) and position == 0:
            position = capital / price
            cost = capital * commission
            capital = -cost
            entry_date = date
            entry_price = price
        
        elif pd.notna(row.get('Sell_Signal')) and position > 0:
            gross = position * price
            cost = gross * commission
            capital = capital + gross - cost
            ret_pct = ((price - entry_price) / entry_price) * 100
            duration = (date - entry_date).days if hasattr(date, 'days') else 0
            try:
                duration = (date - entry_date).days
            except Exception:
                duration = 0
            trades_out.append({
                'buy_date': str(entry_date)[:10], 'sell_date': str(date)[:10],
                'buy_price': entry_price, 'sell_price': price,
                'return_pct': round(ret_pct, 2), 'duration_days': duration
            })
            position = 0
        
        equity.append(capital + position * price)
    
    if position > 0:
        capital += position * float(df_signals['Close'].iloc[-1])
    
    eq_series = pd.Series(equity, index=df_signals.index[:len(equity)])
    return _calculate_metrics(trades_out, eq_series, initial_capital)


# ============================================================
# ANA KARŞILAŞTIRMA FONKSİYONLARI
# ============================================================

STRATEGY_RUNNERS = {
    "momentum": _run_momentum,
    "mean_reversion": _run_mean_reversion,
    "breakout": _run_breakout,
    "macd_crossover": _run_macd_crossover,
    "ensemble_101": _run_ensemble_101
}


def run_strategy(df: pd.DataFrame, strategy_name: str, initial_capital: float = 100000.0) -> dict:
    """
    Tek bir stratejiyi çalıştırır ve performans metriklerini döndürür.
    
    Args:
        df: OHLCV DataFrame
        strategy_name: Strateji adı (STRATEGY_RUNNERS key'lerinden biri)
        initial_capital: Başlangıç sermayesi
    
    Returns:
        dict: Performans metrikleri
    """
    runner = STRATEGY_RUNNERS.get(strategy_name)
    if runner is None:
        return {}
    
    try:
        return runner(df, initial_capital)
    except Exception as e:
        return {
            'total_return_pct': 0, 'sharpe_ratio': 0, 'sortino_ratio': 0,
            'win_rate': 0, 'max_drawdown_pct': 0, 'total_trades': 0,
            'avg_trade_duration': 0, 'profit_factor': 0,
            'best_trade_pct': 0, 'worst_trade_pct': 0,
            'error': str(e)
        }


def compare_strategies(df: pd.DataFrame, strategies: list = None, initial_capital: float = 100000.0) -> pd.DataFrame:
    """
    Birden fazla stratejiyi aynı veri seti üzerinde çalıştırır ve karşılaştırma tablosu üretir.
    
    Args:
        df: OHLCV DataFrame
        strategies: Strateji isimleri listesi (None ise hepsi)
        initial_capital: Başlangıç sermayesi
    
    Returns:
        pd.DataFrame: Karşılaştırma tablosu
    """
    if strategies is None:
        strategies = list(STRATEGY_RUNNERS.keys())
    
    results = []
    for strategy_name in strategies:
        label = STRATEGY_NAMES.get(strategy_name, strategy_name)
        metrics = run_strategy(df, strategy_name, initial_capital)
        metrics['Strateji'] = label
        results.append(metrics)
    
    if not results:
        return pd.DataFrame()
    
    comparison_df = pd.DataFrame(results)
    
    # Kolon sıralaması
    col_order = [
        'Strateji', 'total_return_pct', 'sharpe_ratio', 'sortino_ratio',
        'win_rate', 'max_drawdown_pct', 'total_trades', 'avg_trade_duration',
        'profit_factor', 'best_trade_pct', 'worst_trade_pct'
    ]
    col_order = [c for c in col_order if c in comparison_df.columns]
    comparison_df = comparison_df[col_order]
    
    # Kolon isimleri Türkçeleştir
    comparison_df = comparison_df.rename(columns={
        'total_return_pct': 'Toplam Getiri (%)',
        'sharpe_ratio': 'Sharpe Oranı',
        'sortino_ratio': 'Sortino Oranı',
        'win_rate': 'Kazanma Oranı (%)',
        'max_drawdown_pct': 'Maks Düşüş (%)',
        'total_trades': 'Toplam İşlem',
        'avg_trade_duration': 'Ort. Süre (Gün)',
        'profit_factor': 'Kâr Faktörü',
        'best_trade_pct': 'En İyi İşlem (%)',
        'worst_trade_pct': 'En Kötü İşlem (%)'
    })
    
    return comparison_df


def get_best_strategy(comparison_df: pd.DataFrame) -> dict:
    """
    Karşılaştırma tablosundan en iyi stratejiyi belirler.
    Sıralama kriteri: Sharpe > Win Rate > Max DD (düşük = iyi)
    
    Returns:
        dict: {'strategy': Strateji adı, 'reason': Seçim gerekçesi, 'scores': Metrikler}
    """
    if comparison_df.empty:
        return {'strategy': 'N/A', 'reason': 'Yeterli veri yok', 'scores': {}}
    
    # Normalize edilmiş scoring (0-100 arası)
    df = comparison_df.copy()
    
    scores = {}
    for idx, row in df.iterrows():
        name = row['Strateji']
        score = 0
        
        # Sharpe Ratio (%35 ağırlık)
        sharpe = row.get('Sharpe Oranı', 0)
        score += max(0, min(sharpe * 15, 35))  # Sharpe 2.33 → 35 puan
        
        # Win Rate (%25 ağırlık)
        wr = row.get('Kazanma Oranı (%)', 0)
        score += (wr / 100) * 25
        
        # Max Drawdown (%20 ağırlık — düşük daha iyi)
        dd = row.get('Maks Düşüş (%)', 100)
        score += max(0, (1 - dd/50) * 20)  # DD %0 → 20 puan, DD %50 → 0 puan
        
        # Profit Factor (%20 ağırlık)
        pf = row.get('Kâr Faktörü', 0)
        score += min(pf * 10, 20)  # PF 2.0 → 20 puan
        
        scores[name] = round(score, 1)
    
    best_name = max(scores, key=scores.get)
    best_score = scores[best_name]
    
    best_row = df[df['Strateji'] == best_name].iloc[0]
    reason_parts = []
    if best_row.get('Sharpe Oranı', 0) > 1.0:
        reason_parts.append(f"Yüksek risk-getiri oranı (Sharpe: {best_row['Sharpe Oranı']})")
    if best_row.get('Kazanma Oranı (%)', 0) > 50:
        reason_parts.append(f"İşlemlerin %{best_row['Kazanma Oranı (%)']}inde kâr")
    if best_row.get('Maks Düşüş (%)', 100) < 15:
        reason_parts.append(f"Düşük drawdown (-%{best_row['Maks Düşüş (%)']})")
    
    reason = " | ".join(reason_parts) if reason_parts else "Genel skor en yüksek strateji"
    
    return {
        'strategy': best_name,
        'score': best_score,
        'reason': reason,
        'all_scores': scores
    }
