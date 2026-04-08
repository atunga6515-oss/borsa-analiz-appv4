import sqlite3
import pandas as pd
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    # Portföy tabloları oluştur
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ticker TEXT NOT NULL,
            adet REAL NOT NULL,
            alis_fiyati REAL NOT NULL,
            alis_tarihi TEXT NOT NULL,
            durum TEXT DEFAULT 'ACIK',
            satis_fiyati REAL,
            satis_tarihi TEXT,
            not_text TEXT
        )
    """)
    conn.commit()
    return conn


def alis_yap(username: str, ticker: str, adet: float, fiyat: float, not_text: str = ""):
    """Sanal portföye hisse alımı ekler."""
    conn = _get_conn()
    conn.execute("""
        INSERT INTO portfolio (username, ticker, adet, alis_fiyati, alis_tarihi, durum, not_text)
        VALUES (?, ?, ?, ?, ?, 'ACIK', ?)
    """, (username, ticker.upper(), adet, fiyat, datetime.now().strftime("%Y-%m-%d %H:%M"), not_text))
    conn.commit()
    conn.close()


def satis_yap(trade_id: int, satis_fiyati: float):
    """Açık pozisyonu kapatır (sanal satış)."""
    conn = _get_conn()
    conn.execute("""
        UPDATE portfolio SET durum='KAPALI', satis_fiyati=?, satis_tarihi=?
        WHERE id=?
    """, (satis_fiyati, datetime.now().strftime("%Y-%m-%d %H:%M"), trade_id))
    conn.commit()
    conn.close()


def acik_pozisyonlar(username: str) -> pd.DataFrame:
    """Belirli kullanıcıya ait tüm açık (satılmamış) pozisyonları döndürür."""
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT id, ticker, adet, alis_fiyati, alis_tarihi, not_text FROM portfolio WHERE durum='ACIK' AND username=? ORDER BY alis_tarihi DESC",
        conn, params=(username,)
    )
    conn.close()
    return df


def kapali_pozisyonlar(username: str) -> pd.DataFrame:
    """Belirli kullanıcıya ait tüm kapatılmış (satılmış) pozisyonları döndürür."""
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT id, ticker, adet, alis_fiyati, alis_tarihi, satis_fiyati, satis_tarihi, not_text FROM portfolio WHERE durum='KAPALI' AND username=? ORDER BY satis_tarihi DESC",
        conn, params=(username,)
    )
    conn.close()
    return df


def tum_islemler(username: str) -> pd.DataFrame:
    """Kullanıcıya ait açık ve kapalı tüm işlemleri döndürür."""
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM portfolio WHERE username=? ORDER BY alis_tarihi DESC",
        conn, params=(username,)
    )
    conn.close()
    return df


def islemi_sil(trade_id: int):
    """Bir işlemi tamamen siler."""
    conn = _get_conn()
    conn.execute("DELETE FROM portfolio WHERE id=?", (trade_id,))
    conn.commit()
    conn.close()


def portfoy_temizle(username: str):
    """Kullanıcının tüm portföy verilerini siler."""
    conn = _get_conn()
    conn.execute("DELETE FROM portfolio WHERE username=?", (username,))
    conn.commit()
    conn.close()
