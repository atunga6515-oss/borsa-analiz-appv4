"""
Risk Yönetim Modülü — v3.0.0
ATR bazlı SL/TP, Kelly Criterion, VaR, Korelasyon Matrisi, Pozisyon Büyüklüğü Hesaplayıcı
"""
import pandas as pd
import numpy as np
import ta
from data_loader import fetch_data


# ============================================================
# 1. ATR BAZLI STOP-LOSS / TAKE-PROFIT
# ============================================================

def calculate_atr_stops(df: pd.DataFrame, multiplier_sl: float = 2.0, multiplier_tp: float = 3.0, atr_period: int = 14) -> dict:
    """
    ATR (Average True Range) bazlı dinamik Stop-Loss ve Take-Profit seviyeleri hesaplar.
    
    Returns:
        dict: {
            'atr': ATR değeri,
            'current_price': Güncel fiyat,
            'stop_loss': SL seviyesi,
            'take_profit': TP seviyesi,
            'risk_per_share': Hisse başı risk (₺),
            'reward_per_share': Hisse başı ödül (₺),
            'risk_reward_ratio': R/R oranı
        }
    """
    if df is None or df.empty or len(df) < atr_period + 5:
        return None
    
    atr_indicator = ta.volatility.AverageTrueRange(
        high=df['High'], low=df['Low'], close=df['Close'], window=atr_period
    )
    atr_value = float(atr_indicator.average_true_range().iloc[-1])
    current_price = float(df['Close'].iloc[-1])
    
    stop_loss = round(current_price - (atr_value * multiplier_sl), 2)
    take_profit = round(current_price + (atr_value * multiplier_tp), 2)
    risk_per_share = round(current_price - stop_loss, 2)
    reward_per_share = round(take_profit - current_price, 2)
    
    rr_ratio = round(reward_per_share / risk_per_share, 2) if risk_per_share > 0 else 0.0
    
    return {
        'atr': round(atr_value, 4),
        'current_price': current_price,
        'stop_loss': max(stop_loss, 0.01),  # Negatif SL önle
        'take_profit': take_profit,
        'risk_per_share': risk_per_share,
        'reward_per_share': reward_per_share,
        'risk_reward_ratio': rr_ratio
    }


# ============================================================
# 2. KELLY CRITERION — OPTİMUM POZİSYON BÜYÜKLÜĞÜ
# ============================================================

def calculate_kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> dict:
    """
    Kelly Criterion formülüyle optimum pozisyon büyüklüğünü hesaplar.
    
    Kelly % = W - [(1 - W) / R]
    W = Kazanma oranı (0-1 arası)
    R = Ortalama Kazanç / Ortalama Kayıp
    
    Returns:
        dict: {
            'kelly_pct': Ham Kelly yüzdesi,
            'half_kelly_pct': Yarım Kelly (daha güvenli),
            'quarter_kelly_pct': Çeyrek Kelly (ultra güvenli),
            'win_rate': Kazanma oranı,
            'payoff_ratio': Ödül oranı (R)
        }
    """
    if avg_loss == 0 or win_rate <= 0:
        return {
            'kelly_pct': 0.0,
            'half_kelly_pct': 0.0,
            'quarter_kelly_pct': 0.0,
            'win_rate': win_rate,
            'payoff_ratio': 0.0
        }
    
    w = win_rate / 100.0 if win_rate > 1 else win_rate
    r = abs(avg_win / avg_loss)  # Payoff ratio
    
    kelly = w - ((1 - w) / r)
    kelly = max(kelly, 0.0)  # Negatif Kelly = işlem yapma
    kelly = min(kelly, 1.0)  # Maksimum %100
    
    return {
        'kelly_pct': round(kelly * 100, 2),
        'half_kelly_pct': round(kelly * 50, 2),  # Daha güvenli
        'quarter_kelly_pct': round(kelly * 25, 2),  # Ultra güvenli
        'win_rate': round(w * 100, 2),
        'payoff_ratio': round(r, 2)
    }


# ============================================================
# 3. POZİSYON BÜYÜKLÜĞÜ HESAPLAYICI
# ============================================================

def calculate_position_size(capital: float, risk_pct: float, entry_price: float, stop_loss: float) -> dict:
    """
    Belirli risk yüzdesine göre kaç lot/adet alınacağını hesaplar.
    
    Args:
        capital: Toplam sermaye (₺)
        risk_pct: Kabul edilen risk yüzdesi (örn: 2.0 = %2)
        entry_price: Giriş fiyatı (₺)
        stop_loss: Stop-Loss seviyesi (₺)
    
    Returns:
        dict: {
            'max_risk_amount': Kabul edilen max kayıp (₺),
            'risk_per_share': Hisse başı risk (₺),
            'position_size': Alınabilecek adet (lot),
            'total_investment': Toplam yatırım tutarı (₺),
            'portfolio_allocation_pct': Portföy payı (%)
        }
    """
    if entry_price <= stop_loss or entry_price <= 0 or capital <= 0:
        return {
            'max_risk_amount': 0,
            'risk_per_share': 0,
            'position_size': 0,
            'total_investment': 0,
            'portfolio_allocation_pct': 0
        }
    
    max_risk_amount = capital * (risk_pct / 100.0)
    risk_per_share = entry_price - stop_loss
    position_size = int(max_risk_amount / risk_per_share)  # Tam lot
    total_investment = position_size * entry_price
    allocation_pct = (total_investment / capital) * 100 if capital > 0 else 0
    
    return {
        'max_risk_amount': round(max_risk_amount, 2),
        'risk_per_share': round(risk_per_share, 2),
        'position_size': max(position_size, 0),
        'total_investment': round(total_investment, 2),
        'portfolio_allocation_pct': round(allocation_pct, 2)
    }


# ============================================================
# 4. PORTFÖY GÜNLÜK VALUE-AT-RISK (VaR)
# ============================================================

def calculate_portfolio_var(tickers: list, weights: list = None, confidence: float = 0.95, lookback_days: int = 252) -> dict:
    """
    Portföy düzeyinde parametrik (Varyans-Kovaryans) VaR hesaplar.
    
    Args:
        tickers: Hisse listesi (BIST kodları)
        weights: Ağırlıklar (None ise eşit ağırlık)
        confidence: Güven düzeyi (0.95 = %95)
        lookback_days: Geriye dönük gün sayısı
    
    Returns:
        dict: {
            'daily_var_pct': Günlük VaR (%),
            'daily_var_amount': 100₺ portföy için ₺ VaR,
            'annual_var_pct': Yıllık VaR (%),
            'confidence': Güven düzeyi
        }
    """
    from scipy import stats as scipy_stats
    
    if not tickers:
        return {'daily_var_pct': 0, 'daily_var_amount': 0, 'annual_var_pct': 0, 'confidence': confidence}
    
    # Getiri verilerini topla
    returns_data = {}
    for ticker in tickers:
        try:
            df = fetch_data(ticker, "1d", "1y")
            if df is not None and not df.empty and len(df) > 20:
                returns_data[ticker] = df['Close'].pct_change().dropna()
        except Exception:
            continue
    
    if not returns_data:
        return {'daily_var_pct': 0, 'daily_var_amount': 0, 'annual_var_pct': 0, 'confidence': confidence}
    
    # Ortak tarihli DataFrame oluştur
    returns_df = pd.DataFrame(returns_data).dropna()
    
    if returns_df.empty or len(returns_df) < 20:
        return {'daily_var_pct': 0, 'daily_var_amount': 0, 'annual_var_pct': 0, 'confidence': confidence}
    
    n_assets = len(returns_df.columns)
    
    if weights is None:
        weights = np.array([1.0 / n_assets] * n_assets)
    else:
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize
    
    # Portföy getirisi
    portfolio_returns = returns_df.dot(weights)
    
    # Parametrik VaR (Normal dağılım varsayımı)
    z_score = scipy_stats.norm.ppf(1 - confidence)
    daily_var = abs(z_score * portfolio_returns.std())
    annual_var = daily_var * np.sqrt(252)
    
    return {
        'daily_var_pct': round(daily_var * 100, 4),
        'daily_var_amount': round(daily_var * 100, 2),  # 100₺ portföy baz alındığında
        'annual_var_pct': round(annual_var * 100, 2),
        'confidence': confidence
    }


# ============================================================
# 5. PORTFÖY KORELASYON MATRİSİ
# ============================================================

def calculate_portfolio_correlation(tickers: list, period: str = "6mo") -> pd.DataFrame:
    """
    Portföy içi korelasyon matrisini hesaplar (diversifikasyon analizi).
    
    Returns:
        pd.DataFrame: Korelasyon matrisi (NxN)
    """
    if not tickers or len(tickers) < 2:
        return pd.DataFrame()
    
    price_data = {}
    for ticker in tickers:
        try:
            df = fetch_data(ticker, "1d", period)
            if df is not None and not df.empty:
                price_data[ticker] = df['Close']
        except Exception:
            continue
    
    if len(price_data) < 2:
        return pd.DataFrame()
    
    prices_df = pd.DataFrame(price_data).dropna()
    returns_df = prices_df.pct_change().dropna()
    
    return returns_df.corr().round(3)


# ============================================================
# 6. MAX DRAWDOWN ANALİZİ
# ============================================================

def calculate_max_drawdown_risk(equity_series: pd.Series) -> dict:
    """
    Tarihsel equity serisinden max drawdown ve recovery süresi hesaplar.
    
    Returns:
        dict: {
            'max_drawdown_pct': Maksimum düşüş (%),
            'peak_date': Zirve tarihi,
            'trough_date': Dip tarihi,
            'recovery_days': Toparlanma süresi (gün, None ise henüz toparlanmadı)
        }
    """
    if equity_series is None or len(equity_series) < 5:
        return {'max_drawdown_pct': 0, 'peak_date': None, 'trough_date': None, 'recovery_days': None}
    
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    
    max_dd = drawdown.min()
    trough_idx = drawdown.idxmin()
    peak_idx = equity_series[:trough_idx].idxmax()
    
    # Recovery: Tekrar zirveyı aşan ilk gün
    recovery_days = None
    post_trough = equity_series[trough_idx:]
    peak_value = equity_series[peak_idx]
    recovery_candidates = post_trough[post_trough >= peak_value]
    if len(recovery_candidates) > 0:
        recovery_date = recovery_candidates.index[0]
        recovery_days = (recovery_date - trough_idx).days if hasattr(recovery_date, 'days') or hasattr(trough_idx, 'days') else None
        try:
            recovery_days = (recovery_date - trough_idx).days
        except Exception:
            recovery_days = None
    
    return {
        'max_drawdown_pct': round(abs(max_dd) * 100, 2),
        'peak_date': str(peak_idx)[:10] if peak_idx is not None else None,
        'trough_date': str(trough_idx)[:10] if trough_idx is not None else None,
        'recovery_days': recovery_days
    }


# ============================================================
# 7. RİSK DASHBOARD VERİSİ (WRAPPER)
# ============================================================

def get_risk_dashboard_data(username: str) -> dict:
    """
    Risk dashboard'u için tüm metrikleri derleyen ana fonksiyon.
    
    Returns:
        dict: {
            'positions': Açık pozisyon listesi + SL/TP,
            'total_var': Toplam portföy VaR,
            'correlation_matrix': Korelasyon matrisi,
            'daily_risk_limit': Günlük risk limiti durumu
        }
    """
    import portfolio as pf
    
    positions_df = pf.acik_pozisyonlar(username)
    
    if positions_df.empty:
        return {
            'positions': pd.DataFrame(),
            'total_invested': 0,
            'total_var_amount': 0,
            'tickers': [],
            'correlation_matrix': pd.DataFrame()
        }
    
    tickers = positions_df['ticker'].tolist()
    total_invested = (positions_df['adet'] * positions_df['alis_fiyati']).sum()
    total_var = positions_df['var'].fillna(0).sum()
    
    # Korelasyon matrisi
    corr_matrix = pd.DataFrame()
    if len(tickers) >= 2:
        try:
            corr_matrix = calculate_portfolio_correlation(tickers)
        except Exception:
            pass
    
    return {
        'positions': positions_df,
        'total_invested': round(total_invested, 2),
        'total_var_amount': round(total_var, 2),
        'tickers': tickers,
        'correlation_matrix': corr_matrix
    }
