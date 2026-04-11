import sqlite3
import os
from auth import init_auth_db

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def migrate():
    # 1. Auth DB Başlat
    init_auth_db()
    
    conn = sqlite3.connect(DB_PATH)
    
    # 2. Portfolio tablosuna username ekle
    try:
        conn.execute("ALTER TABLE portfolio ADD COLUMN username TEXT")
        # Mevcut verileri admin1'e ata
        conn.execute("UPDATE portfolio SET username='admin1' WHERE username IS NULL")
        print("Portfolio table updated.")
    except sqlite3.OperationalError:
        print("Portfolio table already updated or error.")
        
    # 3. Scan History tablosuna username ekle
    try:
        conn.execute("ALTER TABLE scan_history ADD COLUMN username TEXT")
        conn.execute("UPDATE scan_history SET username='admin1' WHERE username IS NULL")
        print("Scan history table updated.")
    except sqlite3.OperationalError:
        print("Scan history table already updated or error.")
        
    # 4. Watchlist tablosuna username ekle
    # Watchlist ticker unique olduğu için username ekleyip primary key'i değiştirmek daha karmaşık olabilir.
    # En temizi tabloyu yeni şema ile oluşturmak.
    try:
        conn.execute("ALTER TABLE watchlist ADD COLUMN username TEXT")
        conn.execute("UPDATE watchlist SET username='admin1' WHERE username IS NULL")
        print("Watchlist table updated.")
    except sqlite3.OperationalError:
        print("Watchlist table already updated or error.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
