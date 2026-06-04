import pandas as pd
import numpy as np
import streamlit as st
from indicators import generate_signals_and_score, calculate_indicators

@st.cache_data(ttl=600, show_spinner=False)
def run_advanced_backtest(df_full: pd.DataFrame, initial_capital: float = 100000.0, commission_rate: float = 0.002, lookback_days: int = 180):
    """
    Gelişmiş Portföy Simülasyonu.
    (Güven Skoru >= 65 "AL" -> Tam bakiye ile hisse alınır. Skor < 45 "SAT" -> Eldeki hisseler satılarak nakde dönülür)
    Komisyon (%0.2 varsayılan) hesaba katılır. Max Drawdown ve Kümülatif Kâr tablosu çıkarır.
    """
    if len(df_full) < lookback_days + 50:
         return {"error": "Backtest için yeterli veri yok."}

    # ÇOK ÖNEMLİ: DataFrame üzerindeki indikatörleri backteste başlamadan önce hesapla!
    df_full = calculate_indicators(df_full)

    start_idx = len(df_full) - lookback_days
    if start_idx < 50: start_idx = 50 
    
    capital = initial_capital
    position = 0 # Adet
    trades = []
    
    equity_curve = []
    
    for i in range(start_idx, len(df_full)):

        current_slice = df_full.iloc[:i+1]
        
        result = generate_signals_and_score(current_slice)
        score = result['score']
        
        current_price = df_full['Close'].iloc[i]
        date = df_full.index[i]
        
        # ALIM KARARI
        if score >= 65 and position == 0:
            qty = capital / current_price
            cost = capital * commission_rate
            position = qty
            capital = capital - (qty * current_price) - cost
            trades.append({'Date': date, 'Type': 'BUY', 'Price': current_price, 'Score': score})
            
        # SATIM KARARI (VEYA ZARAR KES)
        elif score < 45 and position > 0:
            gross_value = position * current_price
            cost = gross_value * commission_rate
            capital = capital + gross_value - cost
            trades.append({'Date': date, 'Type': 'SELL', 'Price': current_price, 'Score': score})
            position = 0
            
        # Equity'i kaydet (Nakit + Hissenin o anki değeri)
        current_equity = capital + (position * current_price)
        equity_curve.append({'Date': date, 'Equity': current_equity})

    # Son gün hala pozisyondaysa çıkmış gibi varsayıp nihai equity hesaplayalım
    final_equity = capital + (position * df_full['Close'].iloc[-1])
    
    equity_df = pd.DataFrame(equity_curve).set_index('Date')
    
    # Drawdown Hesaplama
    equity_df['Peak'] = equity_df['Equity'].cummax()
    equity_df['Drawdown'] = (equity_df['Equity'] - equity_df['Peak']) / equity_df['Peak']
    max_drawdown = equity_df['Drawdown'].min() * 100
    
    total_return = ((final_equity - initial_capital) / initial_capital) * 100
    
    # Buy and Hold (Al-Tut) kıyaslaması
    buy_hold_qty = initial_capital / df_full['Close'].iloc[start_idx]
    bh_final = buy_hold_qty * df_full['Close'].iloc[-1]
    bh_return = ((bh_final - initial_capital) / initial_capital) * 100

    # Risksiz Getiri ve Alfa Hesaplamaları
    risk_free_annual = 40.0 # BIST için ortalama yıllık risksiz mevduat getirisi varsayımı
    risk_free_period = risk_free_annual * (lookback_days / 365)
    alpha = total_return - bh_return
    alpha_rf = total_return - risk_free_period

    return {
        "final_equity": final_equity,
        "total_return_pct": total_return,
        "max_drawdown_pct": max_drawdown,
        "buy_and_hold_return_pct": bh_return,
        "risk_free_return_pct": risk_free_period,
        "alpha_bh": alpha,
        "alpha_rf": alpha_rf,
        "number_of_trades": len(trades),
        "equity_curve": equity_df,
        "trades": trades
    }
