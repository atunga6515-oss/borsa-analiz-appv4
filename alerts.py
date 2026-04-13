import streamlit as st
from telegram_utils import send_telegram_report

def check_hybrid_alerts(ticker: str, score: float, current_price: float, kap_sentiment: float, ml_target: float):
    """
    Hibrit Alarm Motoru
    Kriterler:
    - Teknik Skor > 80
    - Haber Duygusu (Sentiment) > 0.7
    - ML Hedef Fiyatı > Mevcut Fiyat
    
    Tetiklenirse, Telegram'a Markdown formatında acil durum raporu gönderir.
    """
    if score > 80 and kap_sentiment > 0.7 and ml_target > current_price:
        # Mesajı bir kez tetiklendiğinde flood atmamak için session_state ile kontrol edebiliriz
        alert_key = f"alert_sent_{ticker}"
        if not st.session_state.get(alert_key, False):
            msg = f"🚨 **KUSURSUZ SETUP ALARMI: {ticker}** 🚨\n\n"
            msg += f"🔥 **Teknik Analiz Skoru:** {score}/100\n"
            msg += f"🗞️ **Haber Duygusu (AI):** {kap_sentiment:.2f} (Pozitif İvme)\n"
            msg += f"💰 **Mevcut Fiyat:** {current_price:.2f} ₺\n"
            msg += f"🤖 **ML Hedef Fiyat:** {ml_target:.2f} ₺\n\n"
            msg += "⚠️ *Bu hisse algoritmanın Otonom Trading (V5) ideal kriterlerini karşılıyor!*"
            
            send_telegram_report(msg)
            # Rapor gönderildiğini kaydet (sayfa yenilendiğinde tekrar atmaması için session state)
            st.session_state[alert_key] = True
            return True
    return False
