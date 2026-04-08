import hashlib
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def hash_password(password: str) -> str:
    """Şifreyi SHA-256 ile hashler."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_auth_db():
    """Kullanıcı tablosunu oluşturur ve admin kullanıcılarını tanımlar."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    
    # Varsayılan kullanıcıları kontrol et ve ekle
    users = ["admin1", "admin2", "admin3"]
    default_pass = hash_password("admin123")
    
    for u in users:
        cursor = conn.execute("SELECT username FROM users WHERE username=?", (u,))
        if not cursor.fetchone():
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (u, default_pass))
    
    conn.commit()
    conn.close()

def verify_login(username, password) -> bool:
    """Kullanıcı girişi kontrolü."""
    conn = sqlite3.connect(DB_PATH)
    p_hash = hash_password(password)
    cursor = conn.execute("SELECT username FROM users WHERE username=? AND password_hash=?", (username, p_hash))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def update_password(username, new_password) -> bool:
    """Şifre güncelleme."""
    try:
        conn = sqlite3.connect(DB_PATH)
        p_hash = hash_password(new_password)
        conn.execute("UPDATE users SET password_hash=? WHERE username=?", (p_hash, username))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
