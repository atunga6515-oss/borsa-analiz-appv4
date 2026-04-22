import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def init_warrant_db():
    """Varant tablosunu başlatır."""
    conn = sqlite3.connect(DB_PATH)
    # Varant Künyesi
    conn.execute("""
        CREATE TABLE IF NOT EXISTS warrants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE,
            underlying TEXT,
            type TEXT, -- CALL or PUT
            strike REAL,
            expiry_date TEXT,
            multiplier REAL,
            issuer TEXT,
            iv REAL DEFAULT 0.50 -- Implied Volatility (Zımni Oynaklık)
        )
    """)
    conn.commit()
    conn.close()

def seed_mock_warrants():
    """Test için örnek varant verilerini doldurur."""
    conn = sqlite3.connect(DB_PATH)
    mock_data = [
        ('THYAA', 'THYAO', 'CALL', 280.0, '2026-06-30', 0.1, 'IS VARANT', 0.45),
        ('THYAB', 'THYAO', 'CALL', 300.0, '2026-06-30', 0.1, 'IS VARANT', 0.48),
        ('THYPA', 'THYAO', 'PUT', 260.0, '2026-06-30', 0.1, 'IS VARANT', 0.50),
        ('AKBBA', 'AKBNK', 'CALL', 45.0, '2026-05-31', 0.5, 'AK VARANT', 0.42),
    ]
    for m in mock_data:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO warrants (ticker, underlying, type, strike, expiry_date, multiplier, issuer, iv) VALUES (?,?,?,?,?,?,?,?)",
                m
            )
        except: pass
    conn.commit()
    conn.close()

def get_warrants_by_underlying(underlying):
    """Belirli bir hisseye (dayanak) ait varantları getirir."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM warrants WHERE underlying=?", conn, params=(underlying,))
    conn.close()
    return df

def update_warrant_iv(ticker, iv):
    """İhraççıdan gelen güncel volatiliteyi günceller."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE warrants SET iv=? WHERE ticker=?", (iv, ticker))
    conn.commit()
    conn.close()
