import requests
import streamlit as st

def send_telegram_report(text: str) -> bool:
    """
    st.secrets içindeki token ve chat_id bilgilerini kullanarak 
    Telegram üzerinden Markdown formatında rapor gönderir.
    """
    token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        st.error("❌ Telegram API bilgileri (TOKEN/CHAT_ID) secrets.toml içinde eksik!")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"  # Veya MarkdownV2
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Telegram Hatası: {response.text}")
            return False
    except Exception as e:
        st.error(f"Telegram Bağlantı Hatası: {str(e)}")
        return False
