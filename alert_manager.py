"""
Alarm Yönetim Modülü — v3.0.0
Fiyat, RSI, SMA Cross, Hacim, Destek/Direnç bazlı alarm CRUD ve tetikleme motoru.
SQLite persistence ile kalıcı alarm desteği.
"""
import sqlite3
import pandas as pd
import os
from datetime import datetime
import pytz

TR_TZ = pytz.timezone("Europe/Istanbul")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

# ============================================================
# ALARM TİPLERİ
# ============================================================
ALERT_TYPES = {
    "FIYAT_USTU": "📈 Fiyat Üstü (Fiyat ≥ Eşik)",
    "FIYAT_ALTI": "📉 Fiyat Altı (Fiyat ≤ Eşik)",
    "RSI_ASIRI_ALIM": "🔴 RSI Aşırı Alım (RSI ≥ Eşik)",
    "RSI_ASIRI_SATIM": "🟢 RSI Aşırı Satım (RSI ≤ Eşik)",
    "SMA_CROSS_UP": "🔼 SMA Yukarı Kesişim (Fiyat SMA'yı yukarı kesiyor)",
    "SMA_CROSS_DOWN": "🔽 SMA Aşağı Kesişim (Fiyat SMA'yı aşağı kesiyor)",
    "VOLUME_SPIKE": "💥 Hacim Patlaması (Hacim ≥ Ortalamanın X katı)",
    "DESTEK_KIRILIM": "⚡ Destek Kırılımı (Fiyat desteğin altına düştü)",
}


def _get_alert_conn():
    """Alarm veritabanı bağlantısını oluşturur ve tabloyu hazırlar."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            ticker TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            threshold REAL NOT NULL,
            status TEXT DEFAULT 'AKTIF',
            note TEXT,
            created_at TEXT NOT NULL,
            triggered_at TEXT,
            triggered_value REAL
        )
    """)
    conn.commit()
    return conn


# ============================================================
# CRUD İŞLEMLERİ
# ============================================================

def create_alert(username: str, ticker: str, alert_type: str, threshold: float, note: str = "") -> int:
    """
    Yeni alarm oluşturur.
    
    Args:
        username: Kullanıcı adı
        ticker: Hisse kodu
        alert_type: Alarm tipi (ALERT_TYPES key'lerinden biri)
        threshold: Eşik değeri (fiyat, RSI, SMA periyodu, hacim çarpanı vb.)
        note: Kullanıcı notu
    
    Returns:
        int: Oluşturulan alarm ID'si
    """
    conn = _get_alert_conn()
    cursor = conn.execute("""
        INSERT INTO alerts (username, ticker, alert_type, threshold, status, note, created_at)
        VALUES (?, ?, ?, ?, 'AKTIF', ?, ?)
    """, (username, ticker.upper(), alert_type, threshold, note,
          datetime.now(TR_TZ).strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    alert_id = cursor.lastrowid
    conn.close()
    return alert_id


def delete_alert(alert_id: int):
    """Alarmı siler."""
    conn = _get_alert_conn()
    conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


def deactivate_alert(alert_id: int):
    """Alarmı devre dışı bırakır (silmeden)."""
    conn = _get_alert_conn()
    conn.execute("UPDATE alerts SET status = 'IPTAL' WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


def get_active_alerts(username: str) -> pd.DataFrame:
    """Kullanıcının aktif alarmlarını döndürür."""
    conn = _get_alert_conn()
    df = pd.read_sql_query(
        "SELECT * FROM alerts WHERE username = ? AND status = 'AKTIF' ORDER BY created_at DESC",
        conn, params=(username,)
    )
    conn.close()
    return df


def get_alert_history(username: str) -> pd.DataFrame:
    """Kullanıcının tetiklenmiş alarm geçmişini döndürür."""
    conn = _get_alert_conn()
    df = pd.read_sql_query(
        "SELECT * FROM alerts WHERE username = ? AND status = 'TETIKLENDI' ORDER BY triggered_at DESC",
        conn, params=(username,)
    )
    conn.close()
    return df


def get_all_alerts(username: str) -> pd.DataFrame:
    """Kullanıcının tüm alarmlarını döndürür (aktif + tetiklenmiş + iptal)."""
    conn = _get_alert_conn()
    df = pd.read_sql_query(
        "SELECT * FROM alerts WHERE username = ? ORDER BY created_at DESC",
        conn, params=(username,)
    )
    conn.close()
    return df


# ============================================================
# ALARM KONTROL MOTORU
# ============================================================

def _trigger_alert(alert_id: int, current_value: float):
    """Alarmı tetiklenmiş olarak işaretler."""
    conn = _get_alert_conn()
    conn.execute("""
        UPDATE alerts SET status = 'TETIKLENDI', triggered_at = ?, triggered_value = ?
        WHERE id = ?
    """, (datetime.now(TR_TZ).strftime("%Y-%m-%d %H:%M:%S"), current_value, alert_id))
    conn.commit()
    conn.close()


def check_alerts(username: str) -> list:
    """
    Tüm aktif alarmları kontrol eder ve tetiklenmesi gerekenleri tetikler.
    
    Returns:
        list: Tetiklenen alarmların listesi [{'id': ..., 'ticker': ..., 'alert_type': ..., 'message': ...}]
    """
    from data_loader import fetch_data, get_live_price
    from indicators import calculate_indicators
    
    active_alerts = get_active_alerts(username)
    if active_alerts.empty:
        return []
    
    triggered = []
    
    # Hisselere göre grupla (aynı hisse için tek seferde veri çek)
    for ticker in active_alerts['ticker'].unique():
        ticker_alerts = active_alerts[active_alerts['ticker'] == ticker]
        
        try:
            # Canlı fiyat
            live_price = get_live_price(ticker)
            if live_price is None or live_price <= 0:
                continue
            
            # İndikatörler için veri çek (sadece gerekli alarm tipleri varsa)
            needs_indicators = ticker_alerts['alert_type'].isin([
                'RSI_ASIRI_ALIM', 'RSI_ASIRI_SATIM', 'SMA_CROSS_UP', 'SMA_CROSS_DOWN', 'VOLUME_SPIKE'
            ]).any()
            
            df = None
            if needs_indicators:
                df = fetch_data(ticker, "1d", "3mo")
                if df is not None and not df.empty:
                    df = calculate_indicators(df)
            
            # Her alarmı kontrol et
            for _, alert in ticker_alerts.iterrows():
                alert_id = alert['id']
                alert_type = alert['alert_type']
                threshold = alert['threshold']
                is_triggered = False
                current_value = live_price
                msg = ""
                
                if alert_type == "FIYAT_USTU":
                    if live_price >= threshold:
                        is_triggered = True
                        msg = f"📈 {ticker}: Fiyat {live_price:.2f}₺ → Eşik {threshold:.2f}₺'nin üzerine çıktı!"
                
                elif alert_type == "FIYAT_ALTI":
                    if live_price <= threshold:
                        is_triggered = True
                        msg = f"📉 {ticker}: Fiyat {live_price:.2f}₺ → Eşik {threshold:.2f}₺'nin altına düştü!"
                
                elif alert_type == "RSI_ASIRI_ALIM" and df is not None and 'RSI_14' in df.columns:
                    rsi_val = float(df['RSI_14'].iloc[-1])
                    current_value = rsi_val
                    if rsi_val >= threshold:
                        is_triggered = True
                        msg = f"🔴 {ticker}: RSI {rsi_val:.1f} → Aşırı alım eşiği {threshold:.0f}'in üzerine çıktı!"
                
                elif alert_type == "RSI_ASIRI_SATIM" and df is not None and 'RSI_14' in df.columns:
                    rsi_val = float(df['RSI_14'].iloc[-1])
                    current_value = rsi_val
                    if rsi_val <= threshold:
                        is_triggered = True
                        msg = f"🟢 {ticker}: RSI {rsi_val:.1f} → Aşırı satım eşiği {threshold:.0f}'in altına düştü!"
                
                elif alert_type == "SMA_CROSS_UP" and df is not None:
                    sma_col = f'SMA_{int(threshold)}'
                    if sma_col in df.columns and len(df) >= 2:
                        prev_close = float(df['Close'].iloc[-2])
                        prev_sma = float(df[sma_col].iloc[-2])
                        curr_sma = float(df[sma_col].iloc[-1])
                        if prev_close < prev_sma and live_price >= curr_sma:
                            is_triggered = True
                            msg = f"🔼 {ticker}: Fiyat {live_price:.2f}₺ → SMA({int(threshold)}) {curr_sma:.2f}₺'yi yukarı kesti!"
                
                elif alert_type == "SMA_CROSS_DOWN" and df is not None:
                    sma_col = f'SMA_{int(threshold)}'
                    if sma_col in df.columns and len(df) >= 2:
                        prev_close = float(df['Close'].iloc[-2])
                        prev_sma = float(df[sma_col].iloc[-2])
                        curr_sma = float(df[sma_col].iloc[-1])
                        if prev_close > prev_sma and live_price <= curr_sma:
                            is_triggered = True
                            msg = f"🔽 {ticker}: Fiyat {live_price:.2f}₺ → SMA({int(threshold)}) {curr_sma:.2f}₺'yi aşağı kesti!"
                
                elif alert_type == "VOLUME_SPIKE" and df is not None and 'Volume' in df.columns:
                    avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1])
                    curr_vol = float(df['Volume'].iloc[-1])
                    current_value = curr_vol
                    if avg_vol > 0 and curr_vol >= avg_vol * threshold:
                        is_triggered = True
                        ratio = curr_vol / avg_vol
                        msg = f"💥 {ticker}: Hacim patlaması! Güncel hacim ortalamanın {ratio:.1f}x katı!"
                
                elif alert_type == "DESTEK_KIRILIM":
                    if live_price <= threshold:
                        is_triggered = True
                        msg = f"⚡ {ticker}: Fiyat {live_price:.2f}₺ → Destek seviyesi {threshold:.2f}₺ kırıldı!"
                
                if is_triggered:
                    _trigger_alert(alert_id, current_value)
                    triggered.append({
                        'id': alert_id,
                        'ticker': ticker,
                        'alert_type': alert_type,
                        'threshold': threshold,
                        'current_value': current_value,
                        'message': msg,
                        'note': alert.get('note', '')
                    })
        
        except Exception:
            continue
    
    return triggered


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def get_alert_type_label(alert_type: str) -> str:
    """Alarm tipi kodunu okunabilir etikete çevirir."""
    return ALERT_TYPES.get(alert_type, alert_type)


def get_alert_type_options() -> list:
    """UI selectbox için alarm tipi seçeneklerini döndürür."""
    return list(ALERT_TYPES.keys())


def get_alert_type_labels() -> dict:
    """Tüm alarm tipi etiketlerini döndürür."""
    return ALERT_TYPES.copy()


def get_default_threshold(alert_type: str) -> float:
    """Alarm tipine göre varsayılan eşik değerini döndürür."""
    defaults = {
        "FIYAT_USTU": 100.0,
        "FIYAT_ALTI": 50.0,
        "RSI_ASIRI_ALIM": 70.0,
        "RSI_ASIRI_SATIM": 30.0,
        "SMA_CROSS_UP": 20.0,  # SMA periyodu
        "SMA_CROSS_DOWN": 50.0,  # SMA periyodu
        "VOLUME_SPIKE": 2.0,  # Ortalama hacmin kaç katı
        "DESTEK_KIRILIM": 50.0,
    }
    return defaults.get(alert_type, 50.0)


def get_threshold_label(alert_type: str) -> str:
    """Alarm tipine göre eşik etiketini döndürür."""
    labels = {
        "FIYAT_USTU": "Hedef Fiyat (₺)",
        "FIYAT_ALTI": "Hedef Fiyat (₺)",
        "RSI_ASIRI_ALIM": "RSI Eşiği",
        "RSI_ASIRI_SATIM": "RSI Eşiği",
        "SMA_CROSS_UP": "SMA Periyodu (gün)",
        "SMA_CROSS_DOWN": "SMA Periyodu (gün)",
        "VOLUME_SPIKE": "Hacim Çarpanı (x)",
        "DESTEK_KIRILIM": "Destek Fiyatı (₺)",
    }
    return labels.get(alert_type, "Eşik Değeri")
