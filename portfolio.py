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
    # Migration (Eski veritabanına yeni kolonları ekleme denemesi)
    try:
        conn.execute("ALTER TABLE portfolio ADD COLUMN sl REAL")
        conn.execute("ALTER TABLE portfolio ADD COLUMN tp REAL")
        conn.execute("ALTER TABLE portfolio ADD COLUMN var REAL")
    except sqlite3.OperationalError:
        pass # Kolonlar zaten ekliyse hatayı yok say
    conn.commit()
    return conn


def alis_yap(username: str, ticker: str, adet: float, fiyat: float, not_text: str = "", sl: float = None, tp: float = None, var_risk: float = None):
    """Sanal portföye hisse alımı ekler."""
    conn = _get_conn()
    conn.execute("""
        INSERT INTO portfolio (username, ticker, adet, alis_fiyati, alis_tarihi, durum, not_text, sl, tp, var)
        VALUES (?, ?, ?, ?, ?, 'ACIK', ?, ?, ?, ?)
    """, (username, ticker.upper(), adet, fiyat, datetime.now().strftime("%Y-%m-%d %H:%M"), not_text, sl, tp, var_risk))
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
        "SELECT id, ticker, adet, alis_fiyati, alis_tarihi, not_text, sl, tp, var FROM portfolio WHERE durum='ACIK' AND username=? ORDER BY alis_tarihi DESC",
        conn, params=(username,)
    )
    conn.close()
    return df


def kapali_pozisyonlar(username: str) -> pd.DataFrame:
    """Belirli kullanıcıya ait tüm kapatılmış (satılmış) pozisyonları döndürür."""
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT id, ticker, adet, alis_fiyati, alis_tarihi, satis_fiyati, satis_tarihi, not_text, sl, tp, var FROM portfolio WHERE durum='KAPALI' AND username=? ORDER BY satis_tarihi DESC",
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


def pozisyon_guncelle(trade_id: int, yeni_adet: float, yeni_fiyat: float):
    """Mevcut bir pozisyonun adet ve maliyet bilgilerini günceller."""
    conn = _get_conn()
    trade = conn.execute("SELECT sl FROM portfolio WHERE id=?", (trade_id,)).fetchone()
    
    new_var = None
    if trade and trade[0] is not None:
        # sl varsa VaR'ı yeniden hesapla
        sl = trade[0]
        new_var = round((yeni_fiyat - sl) * yeni_adet, 2)
        
    if new_var is not None:
        conn.execute("""
            UPDATE portfolio SET adet=?, alis_fiyati=?, var=? WHERE id=?
        """, (yeni_adet, yeni_fiyat, new_var, trade_id))
    else:
        conn.execute("""
            UPDATE portfolio SET adet=?, alis_fiyati=? WHERE id=?
        """, (yeni_adet, yeni_fiyat, trade_id))
        
    conn.commit()
    conn.close()
