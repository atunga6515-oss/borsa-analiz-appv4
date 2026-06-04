import streamlit as st
import pandas as pd
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
from google import genai
from datetime import datetime, timezone, timedelta
import email.utils
import math
import pytz
import os

TR_TZ = pytz.timezone("Europe/Istanbul")

# Gemini API Yapılandırması (Yeni SDK - google-genai)
def _get_client():
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if api_key:
        try:
            return genai.Client(api_key=api_key)
        except Exception as e:
            st.error(f"Gemini Client Başlatma Hatası: {str(e)}")
    else:
        st.warning("⚠️ API Anahtarı bulunamadı! Lütfen '.streamlit/secrets.toml' dosyasına veya sistem ortam değişkenlerine 'GEMINI_API_KEY' ekleyin.")
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def analyze_sentiment_with_ai(news_items):
    """
    Haber listesini Gemini AI ile batch olarak analiz eder.
    Hız için tüm haberleri tek bir prompt ile gönderir.
    """
    client = _get_client()
    if not client:
        return None 

    news_text = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_items)])
    
    prompt = f"""
    Aşağıdaki Borsa İstanbul (BIST) haberlerini analiz et. Her haber için şunları yap:
    1. Kategorize et: [İş İlişkisi, Bilanço, Sermaye Artırımı, Geri Alım, Dava/Olumsuz Gelişme, Diğer]
    2. Puanla (-1.0 ile +1.0 arası): 
       - Pozitif (+0.5 to +1.0): Yüksek montanlı ihaleler, güçlü kârlar, pay geri alım duyuruları.
       - Nötr (-0.4 to +0.4): Olağan genel kurul, rutin bildirimler.
       - Negatif (-0.5 to -1.0): Beklenti altı bilanço, iptal edilen ihaleler, hukuki süreçler.
    3. Neden: Analizin gerekçesi (Kısa ve öz).

    Haberler:
    {news_text}

    SADECE aşağıdaki formatta bir JSON listesi döndür, başka açıklama yapma:
    [
      {{"index": 1, "score": 0.85, "reason": "Yüksek montanlı yeni sözleşme", "category": "İş İlişkisi"}},
      ...
    ]
    """

    try:
        # Yeni SDK ile içerik üretimi (Default olarak en güncel flash modelini dener)
        # Eğer model bulunamazsa veya kota hatası verirse fallback modelleri deneyebiliriz
        for m_name in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
            try:
                response = client.models.generate_content(
                    model=m_name,
                    contents=prompt
                )
                if response and response.text:
                    break
            except Exception:
                continue
        else:
            return None # Hiçbir model yanıt vermedi

    except Exception as e:
        st.error(f"AI Analiz Hatası: {str(e)}")
        return None

    try:
        import re
        raw_text = response.text
        # Çıktıdaki olası metinlerden sadece JSON listesini [ ] ayıkla
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match:
            json_str = match.group(0).strip()
            data = json.loads(json_str)
            return data
        else:
            raise ValueError("Yapay zeka JSON objesi döndürmedi.")
    except Exception as e:
        st.error(f"🤖 AI Çıktı Çözümleme (JSON) Hatası!\nYapay Zeka, beklenen tablolaştırılmış formatın dışına çıktı. Lütfen 'AI Analizi Yap' butonuna tekrar basın.\n\nSistem Şimdilik Kelime (Basit) Analizi İle Devam Ediyor...\nHata Detayı: {str(e)}")
        return None

def fetch_kap_news(ticker):
    """Google News RSS üzerinden KAP odaklı güncel şirket haberlerini çeker."""
    query = urllib.parse.quote(f"{ticker} KAP hisse haberi")
    url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
    
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        xml_data = resp.read()
        root = ET.fromstring(xml_data)
        
        items = []
        for item in root.findall('./channel/item')[:12]:
            items.append({
                "title": item.find('title').text,
                "link": item.find('link').text,
                "date": item.find('pubDate').text
            })
        return items
    except:
        return []

def get_sentiment_summary(ticker):
    """
    Hibrit sistem için hem AI hem de fallback duygu skorunu hesaplar.
    Haber eskidikçe etkisini (Time Decay) azaltır.
    Sonuç: -1 ile +1 arası bir float.
    """
    news = fetch_kap_news(ticker)
    if not news:
        return 0.0, []

    # AI Analizi Dene
    ai_results = analyze_sentiment_with_ai(news)
    
    analyzed_list = []
    total_weighted_score = 0
    total_weight = 0
    now = datetime.now(TR_TZ)
    
    if ai_results:
        # AI Başarılı
        for i, item in enumerate(news):
            ai_data = next((x for x in ai_results if x.get('index') == i+1), None)
            if ai_data:
                try:
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    # Tüm tarihleri karşılaştırma için Istanbul saatine çevir
                    pub_date = pub_date.astimezone(TR_TZ)
                    days_old = (now - pub_date).days
                    date_str = pub_date.strftime("%d.%m.%Y")
                    
                    if days_old > 15:
                        weight = 0.0 # 15 günden eski haberler fiyatlandı, skora etki edemez
                    else:
                        weight = 1.0 / (1 + 0.2 * max(0, days_old))
                except:
                    weight = 0.0
                    date_str = "Tarihsiz"
                    days_old = 99

                score = ai_data.get('score', 0)
                weighted_score = score * weight
                
                analyzed_list.append({
                    "title": item['title'],
                    "score": score,
                    "weighted_score": round(weighted_score, 2),
                    "weight": round(weight, 2),
                    "category": ai_data.get('category', 'Diğer'),
                    "reason": ai_data.get('reason', ''),
                    "date_str": date_str,
                    "days_old": days_old
                })
                total_weighted_score += weighted_score
                total_weight += weight
                
        avg_score = total_weighted_score / total_weight if total_weight > 0 else 0
    else:
        # Fallback (Kelime Bazlı)
        pozitif_kelimeler = ['arttı', 'yüksel', 'kazanç', 'kar ', 'kâr', 'büyü', 'yatırım', 'anlaşma', 'temettü', 'ihale', 'iş ilişkisi']
        negatif_kelimeler = ['düştü', 'zarar', 'azaldı', 'kriz', 'ceza', 'dava', 'iptal', 'olumsuz', 'risk']
        
        for item in news:
            t_low = item['title'].lower()
            p = sum(1 for w in pozitif_kelimeler if w in t_low)
            n = sum(1 for w in negatif_kelimeler if w in t_low)
            score = 0.5 if p > n else -0.5 if n > p else 0
            
            try:
                pub_date = email.utils.parsedate_to_datetime(item['date'])
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                pub_date = pub_date.astimezone(TR_TZ)
                days_old = (now - pub_date).days
                date_str = pub_date.strftime("%d.%m.%Y")
                
                if days_old > 15:
                    weight = 0.0
                else:
                    weight = 1.0 / (1 + 0.2 * max(0, days_old))
            except:
                weight = 0.0
                date_str = "Tarihsiz"
                days_old = 99
                
            weighted_score = score * weight
            analyzed_list.append({
                "title": item['title'],
                "score": score,
                "weighted_score": round(weighted_score, 2),
                "weight": round(weight, 2),
                "category": "Genel Haber",
                "reason": "Kelime bazlı analiz",
                "date_str": date_str,
                "days_old": days_old
            })
            total_weighted_score += weighted_score
            total_weight += weight
            
        avg_score = total_weighted_score / total_weight if total_weight > 0 else 0
        
    return avg_score, analyzed_list

def render_kap_news_panel():
    """Dashboard UI bileşeni."""
    st.title("📰 KAP ve Haber Duygu Analizi (AI Powered)")
    ticker = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO", key="kap_sym").upper().strip()
    
    if st.button("Haber Verilerini Çek & AI Analizi Yap", type="primary"):
        with st.spinner(f"🤖 Gemini AI {ticker} haberlerini analiz ediyor..."):
            avg_score, results = get_sentiment_summary(ticker)
            
            if not results:
                st.warning("Haber bulunamadı.")
                return

            # --- 1. Duygu Barı ---
            st.markdown("### 📊 Genel Haber Algısı")
            # Skoru 0-1 arasına normalize et (Progress bar için)
            norm_score = (avg_score + 1) / 2
            color = "green" if avg_score > 0.1 else "red" if avg_score < -0.1 else "gray"
            
            st.markdown(f"""
                <div style="width:100%; background-color: #262730; border-radius: 10px; padding: 5px;">
                    <div style="width: {norm_score*100}%; background-color: {color}; height: 20px; border-radius: 5px; text-align: center; color: white; font-size: 12px; font-weight: bold;">
                        {avg_score:+.2f}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.divider()

            # --- 2. Haber Kartları ---
            st.markdown("### 🗞️ Son Gelişmeler")
            st.caption("💡 *Zaman Aşımı (Time Decay) Aktif:* Haber eskidikçe etki ağırlığı otomatik olarak azalır.")
            
            for res in results:
                s = res['score']
                ws = res['weighted_score']
                w = res['weight']
                b_color = "#26de81" if s > 0.2 else "#fc5c65" if s < -0.2 else "#fed330"
                t_color = "black" if s >= 0 else "white"
                
                with st.container():
                    st.markdown(f"""
                        <div style="border-left: 5px solid {b_color}; padding: 10px; margin-bottom: 10px; background-color: rgba(255,255,255,0.05); border-radius: 0 5px 5px 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="background-color: {b_color}; color: {t_color}; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: bold;">
                                        {res['category']} | Skor: {s:+.1f}
                                    </span>
                                    <span style="margin-left: 8px; font-size: 0.8rem; color: #a5b1c2;">
                                        🕒 {res.get('date_str', '')} ({res.get('days_old', 0)} gün önce)
                                    </span>
                                </div>
                                <span style="color: gray; font-size: 0.75rem; font-weight: bold;">
                                    Etki: %{w*100:.0f} → {ws:+.2f}
                                </span>
                            </div>
                            <p style="margin: 8px 0 0 0; font-size: 1rem;">{res['title']}</p>
                            <small style="color: gray;"><i>{res['reason']}</i></small>
                        </div>
                    """, unsafe_allow_html=True)

            # Linkler
            kap_url = f"https://www.kap.org.tr/tr/arama/ozet/{ticker}"
            st.info(f"👉 **Resmi KAP Bildirimleri İçin:** [{ticker} KAP Portalı]({kap_url})")
