import sqlite3
import os
import pandas as pd
import ta
from datetime import datetime

# Veritabanı Yolu
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def init_trading_db():
    """Trading disiplin tablosunu başlatır."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trading_discipline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            symbol TEXT,
            is_success BOOLEAN,
            profit_amount REAL,
            target_pct REAL
        )
    """)
    conn.commit()
    conn.close()

def save_daily_result(username, symbol, is_success, amount, target_pct=3.0):
    """Günlük işlem sonucunu kaydeder."""
    init_trading_db()
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO trading_discipline (username, date, symbol, is_success, profit_amount, target_pct) VALUES (?,?,?,?,?,?)",
        (username, today, symbol, is_success, amount, target_pct)
    )
    conn.commit()
    conn.close()

def get_trading_stats(username):
    """Kullanıcının disiplin istatistiklerini döndürür."""
    init_trading_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM trading_discipline WHERE username=?", conn, params=(username,))
    conn.close()
    
    if df.empty:
        return {
            "total_days": 0,
            "success_days": 0,
            "win_rate": 0,
            "total_profit": 0,
            "history": []
        }
    
    success_days = df[df['is_success'] == 1].shape[0]
    total_days = df.shape[0]
    
    return {
        "total_days": total_days,
        "success_days": success_days,
        "win_rate": round((success_days / total_days) * 100, 1) if total_days > 0 else 0,
        "total_profit": df['profit_amount'].sum(),
        "history": df.to_dict('records')
    }

def calculate_atr_volatility(df, window=10):
    """Hissenin volatilite uygunluğunu kontrol eder (ATR bazlı)."""
    if df.empty or len(df) < window + 1:
        return {"atr_pct": 0, "is_suitable": False}
    
    # ATR Hesapla
    atr = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=window).iloc[-1]
    last_price = df['Close'].iloc[-1]
    
    atr_pct = (atr / last_price) * 100
    
    return {
        "atr_val": round(atr, 2),
        "atr_pct": round(atr_pct, 2),
        "is_suitable": atr_pct >= 3.0 # Hedeflenen %3 marjı sağlayabilecek volatilite var mı?
    }

def get_risk_levels(price, target_pct=3.0, stop_pct=1.5):
    """Alım fiyatına göre hedef ve stop seviyelerini döner."""
    target_price = price * (1 + target_pct / 100)
    stop_price = price * (1 - stop_pct / 100)
    return {
        "target": round(target_price, 2),
        "stop": round(stop_price, 2)
    }
