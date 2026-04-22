import sqlite3
import os
import pandas as pd
import ta
from datetime import datetime

# Veritabanı Yolu
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def init_trading_db():
    """Trading disiplin tablosunu başlatır veya yeniler."""
    conn = sqlite3.connect(DB_PATH)
    
    # Ana Tablo: Strateji ve Duygu eklendi
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trading_discipline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            symbol TEXT,
            is_success BOOLEAN,
            profit_amount REAL,
            target_pct REAL,
            strategy TEXT DEFAULT 'Bilinmiyor',
            emotion TEXT DEFAULT 'Nötr'
        )
    """)
    
    # Eski formattan yeni formata geçiş kolonlarını ekle (Eğer yoksa)
    try:
        conn.execute("ALTER TABLE trading_discipline ADD COLUMN strategy TEXT DEFAULT 'Bilinmiyor'")
        conn.execute("ALTER TABLE trading_discipline ADD COLUMN emotion TEXT DEFAULT 'Nötr'")
    except sqlite3.OperationalError:
        pass # Kolonlar zaten var
        
    conn.commit()
    conn.close()

def save_daily_result(username, symbol, is_success, amount, target_pct=3.0, strategy="Bilinmiyor", emotion="Nötr"):
    """Günlük işlem sonucunu detaylarıyla kaydeder."""
    init_trading_db()
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO trading_discipline (username, date, symbol, is_success, profit_amount, target_pct, strategy, emotion) VALUES (?,?,?,?,?,?,?,?)",
        (username, today, symbol, is_success, amount, target_pct, strategy, emotion)
    )
    conn.commit()
    conn.close()

def check_cooldown_status(username) -> dict:
    """Kullanıcının o gün içerisinde 3 zararlı işlemi olup olmadığını kontrol eder."""
    init_trading_db()
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Bugün girilen ZARARLI işlemleri say
    df = pd.read_sql_query(
        "SELECT * FROM trading_discipline WHERE username=? AND date=? AND is_success=0", 
        conn, params=(username, today)
    )
    conn.close()
    
    loss_count = len(df)
    is_cooldown = loss_count >= 3
    
    return {
        "is_cooldown": is_cooldown,
        "loss_count": loss_count,
        "message": "🛑 3 Kez Stop Oldunuz. Bugün yeni işlem girmek psikolojiniz için tehlikelidir." if is_cooldown else f"Bugünkü Stop Sayısı: {loss_count}/3"
    }

def get_trading_stats(username):
    """Kullanıcının detaylı duygu ve strateji analitiklerini döndürür."""
    init_trading_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM trading_discipline WHERE username=? ORDER BY id DESC", conn, params=(username,))
    conn.close()
    
    if df.empty:
        return {
            "total_days": 0,
            "success_days": 0,
            "win_rate": 0,
            "total_profit": 0,
            "history": [],
            "streak": 0,
            "best_strategy": "-",
            "worst_emotion": "-"
        }
    
    success_days = df[df['is_success'] == 1].shape[0]
    total_days = df.shape[0]
    total_profit = df['profit_amount'].sum()
    
    # Günlük Kâr Serisi (Streak) - En son işlemden geriye doğru ardışık kazanç/kayıp
    streak = 0
    df_sorted = df.sort_values(by='id', ascending=False) # En yeniden en eskiye
    for _, row in df_sorted.iterrows():
        if row['is_success'] == 1:
            if streak >= 0: streak += 1
            else: break # Kayıp serisi bitti
        else:
            if streak <= 0: streak -= 1
            else: break # Kazanç serisi bitti
            
    # Strateji & Duygu Analizi
    best_strategy = "-"
    if 'strategy' in df.columns:
        strat_win_rates = df.groupby('strategy')['is_success'].mean()
        if not strat_win_rates.empty and len(df) >= 3:
            best_strategy = f"{strat_win_rates.idxmax()} (%{strat_win_rates.max()*100:.0f} Win Rate)"
            
    worst_emotion = "-"
    if 'emotion' in df.columns:
        emotion_loss_rates = 1 - df.groupby('emotion')['is_success'].mean() # Kaybetme oranı
        if not emotion_loss_rates.empty and len(df) >= 3:
            worst_emotion = f"{emotion_loss_rates.idxmax()} (%{emotion_loss_rates.max()*100:.0f} Kayıp Oranı)"
            
    return {
        "total_days": total_days,
        "success_days": success_days,
        "win_rate": round((success_days / total_days) * 100, 1) if total_days > 0 else 0,
        "total_profit": total_profit,
        "history": df.to_dict('records'),
        "streak": streak,
        "best_strategy": best_strategy,
        "worst_emotion": worst_emotion,
        "raw_df": df
    }

def calculate_position_size(balance: float, risk_pct: float, current_px: float, stop_px: float) -> dict:
    """
    Sermaye Koruma Modeli: Göze alınan risk yüzdesine göre maksimum lot (adet) ve tutarı hesaplar.
    """
    if current_px <= stop_px or current_px <= 0 or balance <= 0:
        return {"max_shares": 0, "max_investment": 0, "risk_amount": 0}
        
    risk_amount = balance * (risk_pct / 100.0) # Paramın yüzde kaçını kaybetmeye hazırım?
    risk_per_share = current_px - stop_px     # Adet başına alacağım zarar
    
    max_shares = int(risk_amount / risk_per_share)
    max_investment = max_shares * current_px
    
    # Eger maks yatirim tutari bakiyeyi asarsa (ki cok dusuk stop koymussa asabilir), bakiye ile sinirla.
    if max_investment > balance:
        max_shares = int(balance / current_px)
        max_investment = max_shares * current_px
        
    return {
        "max_shares": max_shares,
        "max_investment": round(max_investment, 2),
        "risk_amount": round(risk_amount, 2),
        "actual_risk_taken": round(max_shares * risk_per_share, 2)
    }

def get_compounding_projection(balance: float, target_pct: float = 3.0, current_day: int = 1, total_days: int = 20) -> list:
    """
    Kullanıcının hedeflerine uyması halinde elde edeceği Bileşik Getiri (Compounding) simülasyonunu oluşturur.
    """
    proj = []
    curr_balance = balance
    for day in range(1, total_days + 1):
        is_past = day <= current_day
        proj.append({
            "Gün": day,
            "Beklenen Bakiye (₺)": round(curr_balance, 2),
            "Durum": "Tamamlandı" if is_past else "Gelecek"
        })
        curr_balance = curr_balance * (1 + (target_pct / 100.0))
        
    return proj

def get_risk_levels(price, target_pct=3.0, stop_pct=1.5):
    """Alım fiyatına göre hedef ve stop seviyelerini döner."""
    target_price = price * (1 + target_pct / 100)
    stop_price = price * (1 - stop_pct / 100)
    return {
        "target": round(target_price, 2),
        "stop": round(stop_price, 2)
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
        "is_suitable": atr_pct >= 3.0 
    }
