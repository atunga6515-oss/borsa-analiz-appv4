import portfolio as pf
import sqlite3
import os

# Veritabanını bul
db_path = os.path.join(os.getcwd(), "bist_cache.db")
print(f"DB Path: {db_path}")

# Mevcut bir ID bul
conn = sqlite3.connect(db_path)
trade = conn.execute("SELECT id, ticker, adet, alis_fiyati FROM portfolio WHERE durum='ACIK' LIMIT 1").fetchone()
conn.close()

if trade:
    trade_id, ticker, old_adet, old_fiyat = trade
    print(f"Testing for {ticker} (ID: {trade_id}). Old Adet: {old_adet}, Old Fiyat: {old_fiyat}")
    
    new_adet = old_adet + 10
    new_fiyat = old_fiyat + 1
    
    pf.pozisyon_guncelle(trade_id, new_adet, new_fiyat)
    print("Update called.")
    
    # Tekrar kontrol et
    conn = sqlite3.connect(db_path)
    new_trade = conn.execute("SELECT id, ticker, adet, alis_fiyati FROM portfolio WHERE id=?", (trade_id,)).fetchone()
    conn.close()
    
    print(f"New state: {new_trade}")
    if new_trade[2] == new_adet and new_trade[3] == new_fiyat:
        print("SUCCESS: Database persisted.")
    else:
        print("FAILED: Database did not match.")
else:
    print("No open trades found to test.")
