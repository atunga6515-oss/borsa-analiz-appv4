import streamlit as st
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_loader import fetch_data, get_db_stats, clear_db, get_ticker_db_info, get_live_price
from indicators import calculate_indicators, generate_signals_and_score, get_market_regime
from visualizations import create_advanced_chart, create_ml_chart, create_equity_curve_chart
from screener import (run_screener, BIST30_SYMBOLS, BIST100_SYMBOLS, BIST_ALL_SYMBOLS, 
                      save_scan_results, get_sector_list, filter_by_sector, 
                      get_scan_history, get_persistent_signals,
                      add_to_watchlist, remove_from_watchlist, get_watchlist)
from ml_forecast import generate_ml_forecast
from telegram_utils import send_telegram_report
from advanced_backtest import run_advanced_backtest
from support_resistance import calculate_best_zones
from alerts import check_hybrid_alerts
import portfolio as pf
import plotly.express as px
from kap_news import render_kap_news_panel, get_sentiment_summary
from top_picks import (find_top_picks, save_top_picks_history, 
                        get_top_picks_history_dates, get_top_picks_by_date)
import trading_goal_manager as tgm
import auth

# Kimlik doğrulama sistemini başlat
auth.init_auth_db()

st.set_page_config(page_title="BIST Broker Analysis Terminal", layout="wide", initial_sidebar_state="expanded")

# --- PROFESYONEL TERMİNAL TASARIMI (SABİT KONTRAST VE OKUNABİLİRLİK) ---
if not st.session_state.get('logged_in', False):
    st.markdown("""
    <style>
        :root {
            --terminal-bg: #11141a; 
        --content-bg: #161a21; 
        --emerald: #4ade80;   
        --soft-white: #f1f5f9;  
        --sidebar-bg: #0f172a;
        --card-bg: #1e293b;
    }
    
    /* Global Arka Plan ve Yazı */
    .stApp {
        background-color: var(--terminal-bg) !important;
        color: var(--soft-white) !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid rgba(74, 222, 128, 0.1);
    }
    
    .main {
        background: var(--content-bg) !important;
    }
    
    /* Başlıklar */
    h1, h2, h3, h4, h5, h6 {
        color: var(--emerald) !important;
        font-weight: 700 !important;
    }

    /* BEYAZ ÜZERİNE BEYAZ SORUNUNU GİDER */
    /* Expander Gelişmiş Tasarımı */
    [data-testid="stExpander"] {
        background-color: var(--card-bg) !important;
        border: 1px solid rgba(74, 222, 128, 0.1) !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stExpander"] details {
        background-color: var(--card-bg) !important;
    }
    
    /* Expander (Açılır Kapanır Menü / Sidebar ve Ana Ekran için) */
    [data-testid="stExpander"] {
        background-color: #0f172a !important;
        border: 1px solid rgba(74, 222, 128, 0.2) !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary {
        background-color: transparent !important;
        color: var(--emerald) !important;
        font-weight: 600 !important;
    }
    [data-testid="stExpander"] summary:hover {
        background-color: rgba(255,255,255, 0.05) !important;
    }
    [data-testid="stExpander"] div[role="region"] {
        background-color: transparent !important;
        color: var(--soft-white) !important;
    }


    /* Sekmeler (Tabs) */
    button[data-baseweb="tab"] {
        color: var(--soft-white) !important;
    }
    
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--emerald) !important;
        border-bottom-color: var(--emerald) !important;
    }

    /* Selectbox ve Inputlar (Fokus ve Seçenek Listesi) */
    div[data-baseweb="select"] div, input, textarea {
        color: var(--soft-white) !important;
        background-color: #0f172a !important;
        border-color: rgba(74, 222, 128, 0.2) !important;
    }
    
    div[role="listbox"] ul {
        background-color: #1e293b !important;
    }
    
    div[role="option"] {
        color: var(--soft-white) !important;
    }

    /* Metrik Kartları */
    div[data-testid="metric-container"] {
        background-color: #1e293b !important;
        border: 1px solid rgba(74, 222, 128, 0.2) !important;
        padding: 1rem !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] *,
    [data-testid="stMetricLabel"] div,
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] span {
        color: #f8fafc !important; /* Çok açık, parlak gri/beyaz (Göz yormayan, okunaklı) */
        opacity: 1 !important;
    }

    div[data-testid="stMetricValue"] {
        color: var(--emerald) !important;
    }

    /* Veri Tabloları */
    .stDataFrame {
        background-color: #0f172a !important;
    }

    /* Butonlar */
    .stButton>button {
        background-color: #1e293b !important;
        color: var(--emerald) !important;
        border: 1px solid var(--emerald) !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton>button:hover {
        background-color: var(--emerald) !important;
        color: #064e3b !important;
    }

    /* Sidebar Yazıları */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] span {
        color: var(--soft-white) !important;
        opacity: 1 !important;
    }
    
    div[data-baseweb="radio"] div[aria-checked="true"] p {
        color: var(--emerald) !important;
        font-weight: bold !important;
    }

    /* Fokus Çerçevelerini Temizle */
    button:focus, div:focus {
        outline: none !important;
    }
</style>
""", unsafe_allow_html=True)

def render_login_page():
    """Modern Finans Terminali konseptli Glassmorphism Giriş Sayfası (Kusursuz Hizalanmış ve Düzeltilmiş)"""
    from data_loader import get_live_price_with_change
    
    @st.cache_data(ttl=60)
    def fetch_market_snapshot():
        symbols_map = {
            "BIST 100": "XU100.IS", "BIST 30": "XU030.IS", 
            "USD/TRY": "USDTRY=X", "EUR/TRY": "EURTRY=X",
            "BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD",
            "Altın Ons": "GC=F", "Gümüş Ons": "SI=F",
            "Brent Petrol": "BZ=F"
        }
        
        def fetch_single(label, sym):
            try:
                # Paralel çekimde her biri bağımsızdır, timeout riskini azaltır
                d = yf.download(sym, period="5d", interval="1d", progress=False, auto_adjust=False, repair=True)
                if not d.empty:
                    # MultiIndex kontrolü (tek sembolde genelde olmaz ama garantiye alalım)
                    if isinstance(d.columns, pd.MultiIndex):
                        d.columns = d.columns.droplevel(1) if sym in d.columns.get_level_values(1) else d.columns.droplevel(0)
                    
                    ticker_data = d.dropna(subset=['Close'])
                    if not ticker_data.empty:
                        px = float(ticker_data['Close'].iloc[-1])
                        prev_px = float(ticker_data['Close'].iloc[-2]) if len(ticker_data) >= 2 else px
                        return label, {"val": px, "chg": px - prev_px}
                return label, {"val": 0, "chg": 0}
            except:
                return label, {"val": 0, "chg": 0}

        # Paralel İşlemi Başlat
        res = {label: {"val": 0, "chg": 0} for label in symbols_map}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_label = {executor.submit(fetch_single, label, sym): label for label, sym in symbols_map.items()}
            for future in as_completed(future_to_label):
                label = future_to_label[future]
                try:
                    l, val_res = future.result()
                    res[l] = val_res
                except:
                    pass

        # Altın/Gümüş Gram hesaplaması
        usd = res.get("USD/TRY", {}).get("val", 0)
        usd_chg = res.get("USD/TRY", {}).get("chg", 0)
        if usd > 0:
            for metal in ["Altın Ons", "Gümüş Ons"]:
                if res.get(metal, {}).get("val", 0) > 0:
                    ons_val = res[metal]["val"]
                    ons_chg = res[metal]["chg"]
                    yeni_gram = (ons_val / 31.1035) * usd
                    eski_gram = ((ons_val - ons_chg) / 31.1035) * (usd - usd_chg)
                    res[metal.replace("Ons", "Gram")] = {"val": yeni_gram, "chg": yeni_gram - eski_gram}
        return res

    market_data = fetch_market_snapshot()

    # CSS Tasarım Sistemi
    st.markdown(f"""
    <style>
        .stApp {{ background: linear-gradient(135deg, #000428, #004e92) fixed; }}
        .stApp::before {{
            content: ""; position: absolute; top:0; left:0; width:100%; height:100%;
            background-image: linear-gradient(0deg, transparent 24%, rgba(255,255,255,.05) 25%, rgba(255,255,255,.05) 26%, transparent 27%, transparent 74%, rgba(255,255,255,.05) 75%, rgba(255,255,255,.05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(255,255,255,.05) 25%, rgba(255,255,255,.05) 26%, transparent 27%, transparent 74%, rgba(255,255,255,.05) 75%, rgba(255,255,255,.05) 76%, transparent 77%, transparent);
            background-size: 50px 50px; z-index: 0;
        }}
        [data-testid="stSidebar"], [data-testid="stHeader"] {{ display: none !important; }}

        /* Streamlit Varsayılan Boşluklarını Sıfırla (Force) */
        [data-testid="stAppViewBlockContainer"] {{
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }}
        .main .block-container {{
            padding-top: 0rem !important;
            max-width: 100%;
        }}
        header {{
            visibility: hidden;
            height: 0px;
        }}

        /* Merkezi Panel */
        .login-panel {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px 40px 40px 40px;
            box-shadow: 0 25px 45px rgba(0,0,0,0.4);
            margin: -30px auto 30px auto; /* Negatif marjin ile yukarı çekildi */
        }}
        
        /* Başlık Kutusu */
        .p-header {{ 
            text-align: center; 
            margin-bottom: 30px; 
            background: rgba(0,0,0,0.4); 
            padding: 20px; 
            border-radius: 15px; 
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .p-title {{ font-size: 2.2rem; font-weight: 900; color: white; margin: 0; letter-spacing: -1.5px; line-height: 1; }}
        .p-subtitle {{ font-size: 0.85rem; color: #3498db; font-weight: bold; text-transform: uppercase; margin-top: 8px; }}

        /* Sabit Alt Veri Çubuğu (Fixed Bottom Bar) */
        .market-bar {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(15px);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            justify-content: space-evenly;
            align-items: center;
            padding: 12px 0;
            z-index: 1000;
            overflow-x: auto;
        }}
        .m-card-bottom {{ 
            min-width: 110px; 
            text-align: center; 
            padding: 5px 10px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.05); /* Yönlendirme eklenecek */
        }}
        .m-card-up {{ border-bottom: 2px solid #26de81; background: rgba(38, 222, 129, 0.05); }}
        .m-card-down {{ border-bottom: 2px solid #ff4757; background: rgba(255, 71, 87, 0.05); }}
        
        .m-lbl {{ color: #aaa; font-size: 0.65rem; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; }}
        .m-val {{ font-weight: 900; font-size: 0.95rem; margin-top: 3px; }}
        .val-up {{ color: #26de81; }}
        .val-down {{ color: #ff4757; }}

        /* Streamlit Overrides & UX Fixes */
        div[data-testid="stTextInput"] p {{ color: white !important; font-weight: bold !important; letter-spacing: 0.5px; margin-bottom: 5px; }}
        div[data-testid="stTextInput"] input {{ background-color: rgba(0,0,0,0.5) !important; color: white !important; border: 1px solid rgba(255,255,255,0.1) !important; }}
        button[kind="primaryFormSubmit"] {{ background-color: #26de81 !important; color: black !important; font-weight: bold !important; border-radius: 10px !important; height: 3.2rem !important; }}
        div[data-testid="stForm"] {{ background: transparent !important; border: none !important; padding: 0 !important; }}
    </style>
    """, unsafe_allow_html=True)


    # Merkezi Yerleşim
    _, col, _ = st.columns([1, 2.5, 1])
    with col:
        st.markdown('<div class="login-panel">', unsafe_allow_html=True)
        
        # Başlık ve Slogan (Kutu İçinde)
        st.markdown("""
            <div class="p-header">
                <div class="p-title">BIST Broker Terminal</div>
                <div class="p-subtitle">AI-Powered Hybrid Analysis</div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("auth_form_final"):
            u_input = st.text_input("Kullanıcı Adı", placeholder="user")
            p_input = st.text_input("Giriş Şifresi", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sisteme Giriş Yap", type="primary", width='stretch')
            
            if submitted:
                if auth.verify_login(u_input, p_input):
                    st.session_state.logged_in = True
                    st.session_state.username = u_input
                    st.rerun()
                else:
                    st.error("🔑 Hatalı Giriş Bilgileri")
                    
        st.markdown('</div>', unsafe_allow_html=True)

    # Tam Ekran Sabit Veri Kartları (Alt Bar)
    cards_html = ""
    for lbl, data in market_data.items():
        val = data.get("val", 0)
        chg = data.get("chg", 0)
        
        fmt = f"{val:,.0f}" if val > 1000 else f"{val:.2f}"
        if val == 0: fmt = "N/A"
        
        arrow = "▲" if chg >= 0 else "▼"
        c_class = "m-card-up" if chg >= 0 else "m-card-down"
        v_class = "val-up" if chg >= 0 else "val-down"
        
        cards_html += f'<div class="m-card-bottom {c_class}"><div class="m-lbl">{lbl}</div><div class="m-val {v_class}">{arrow} {fmt}</div></div>'
    
    st.markdown(f'<div class="market-bar">{cards_html}</div>', unsafe_allow_html=True)

def main():
    # --- OTURUM YÖNETİMİ ---
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    if not st.session_state.logged_in:
        render_login_page()
        return # Giriş yapılana kadar alt tarafı gösterme

    # Giriş yapan kullanıcı bilgisi
    st.sidebar.markdown(f"👤 **Kullanıcı:** {st.session_state.username}")
    if st.sidebar.button("🚪 Çıkış Yap"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    current_user = st.session_state.username

    # Navigasyon
    mode = st.sidebar.radio("📁 Terminal Modülleri", [
        "📊 Hisse Profili ve Derinlik Analizi",
        "🔍 Piyasa Tarama Terminali (Screener)",
        "🤖 Öngörüsel Model Analizi (Predictive Engine)",
        "💼 Gelişmiş Backtest",
        "📈 Sanal Portföy",
        "📰 KAP ve Haberler",
        "🌟 Haber Alpha (Alpha Discovery)",
        "🏆 Stratejik Seçki (Top Picks)",
        "🎯 20 Günlük Trader Disiplini",
        "🔒 Profil ve Güvenlik"
    ])
    
    st.sidebar.markdown("---")
    
    # SQLite Veritabanı Durum Paneli
    with st.sidebar.expander("💾 Veritabanı (SQLite Cache)"):
        db_stats = get_db_stats()
        st.write(f"📦 **Kayıtlı Hisse:** {db_stats['unique_tickers']}")
        st.write(f"📊 **Toplam Satır:** {db_stats['total_rows']:,}")
        st.write(f"💿 **DB Boyutu:** {db_stats['db_size_mb']} MB")
        
        st.markdown("---")
        st.write("🔍 **Hisse Verisi Sorgula**")
        q_sym = st.text_input("Hisse Kodu:", "", key="db_query").upper()
        if q_sym:
            t_info = get_ticker_db_info(q_sym)
            if t_info:
                st.success(f"✅ İlk Tarih: {t_info['first_date']}\n\n✅ Son Tarih: {t_info['last_date']}\n\n✅ Satır: {t_info['row_count']}")
            else:
                st.error("Veri yok.")
        
        st.caption("Veriler ilk çekildiğinde SQLite'a kaydedilir. Sonraki isteklerde sadece eksik günler indirilir.")
        if st.button("🗑️ Cache'i Temizle"):
            clear_db()
            st.cache_data.clear()
            st.success("Veritabanı temizlendi!")
            st.rerun()

    

    if mode == "📊 Hisse Profili ve Derinlik Analizi":
        st.title("📊 Hisse Profili ve Derinlik Analizi")
        sym = st.sidebar.text_input("Hisse Kodu (Örn: EREGL)", "THYAO")
        if sym:
            with st.spinner("Veriler işleniyor..."):
                df = fetch_data(sym, "1d", "1y")
            if df.empty:
                st.error("Veri bulunamadı.")
                return
                
            # Piyasa Rejimi (XU100)
            xu100_df = fetch_data("XU100", "1d", "1y")
            market_regime = get_market_regime(xu100_df)
            
            df = calculate_indicators(df)
            
            # --- Hibrit Duygu Analizi Çek ---
            with st.spinner("🤖 Haber Akışı AI ile analiz ediliyor..."):
                sent_score, news_list = get_sentiment_summary(sym)
                
            res = generate_signals_and_score(df, market_regime=market_regime, sentiment_score=sent_score)
            live_px = df['Close'].iloc[-1]
            sr_data = calculate_best_zones(df)
            
            c1, c2 = st.columns([1.2, 2])
            with c1:
                st.markdown(f"### 🛡️ {sym.upper()} Hibrit Profil")
                
                # --- PREMIUM STYLED METRICS ---
                decision_label = res.get('decision', 'N/A')
                conv_label = res.get('conviction_level', 'ORTA ⚖️')
                final_score = res.get('score', 0)
                pgs_score = res.get('pgs', 0)
                
                # Karar Kartı
                d_color = "#2d6a2e" if "Lideri" in decision_label or "Pozitif" in decision_label else "#641e16" if "Negatif" in decision_label or "Baskı" in decision_label else "#1a5276"
                st.markdown(f"""
                    <div style="background-color: {d_color}; padding: 15px; border-radius: 10px; border-left: 8px solid rgba(255,255,255,0.3); margin-bottom: 15px;">
                        <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7); font-weight: bold; text-transform: uppercase;">Stratejik Karar</div>
                        <div style="font-size: 1.4rem; color: white; font-weight: 900;">{decision_label}</div>
                    </div>
                """, unsafe_allow_html=True)

                # Güven Seviyesi Kartı
                c_color = "#0b5345" if "YÜKSEK" in conv_label or "GEM" in conv_label else "#784212" if "ORTA" in conv_label else "#641e16"
                st.markdown(f"""
                    <div style="background-color: {c_color}; padding: 12px; border-radius: 10px; border-left: 8px solid rgba(255,255,255,0.3); margin-bottom: 15px;">
                        <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7); font-weight: bold; text-transform: uppercase;">Güven Seviyesi (Conviction)</div>
                        <div style="font-size: 1.1rem; color: white; font-weight: bold;">{conv_label}</div>
                    </div>
                """, unsafe_allow_html=True)

                # Skorlar (Gelişmiş Metrik Barı)
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.markdown(f"""
                        <div style="text-align: center; border: 1px solid #3e3e3e; padding: 10px; border-radius: 10px; background-color: #1e1e1e;">
                            <div style="color: #00ff00; font-size: 1.5rem; font-weight: bold;">{final_score}</div>
                            <div style="color: gray; font-size: 0.7rem;">Hibrit Potansiyel</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_s2:
                    st.markdown(f"""
                        <div style="text-align: center; border: 1px solid #3e3e3e; padding: 10px; border-radius: 10px; background-color: #1e1e1e;">
                            <div style="color: #fed330; font-size: 1.5rem; font-weight: bold;">{pgs_score}</div>
                            <div style="color: gray; font-size: 0.7rem;">Güvenlik (PGS)</div>
                        </div>
                    """, unsafe_allow_html=True)

                # Duygu Barı (Küçük Versiyon)
                if news_list:
                    norm_s = (sent_score + 1) / 2
                    s_color = "#26de81" if sent_score > 0.1 else "#fc5c65" if sent_score < -0.1 else "#fed330"
                    st.markdown(f"""
                        <div style="font-size: 0.8rem; margin: 15px 0 5px 0; color: gray;">📰 AI Haber Duygu Algısı: {sent_score:+.2f}</div>
                        <div style="width:100%; background-color: #262730; border-radius: 5px; height: 12px; border: 1px solid #444;">
                            <div style="width: {norm_s*100}%; background-color: {s_color}; height: 10px; border-radius: 5px; transition: width 1s;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Hibrit Analiz Özeti
                st.markdown("---")
                st.subheader("📝 Hibrit Analiz Özeti")
                st.info(res.get('summary', 'Analiz sonucu bekleniyor...'))
                
                st.write("**🛡️ Risk Yönetimi (ATR Bazlı):**")
                risk_data = res.get('risk', {})
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("Stop Loss", f"{risk_data.get('SL', 0):.2f}")
                rc2.metric("Hedef 1 (TP1)", f"{risk_data.get('TP1', 0):.2f}")
                rc3.metric("Hedef 2 (TP2)", f"{risk_data.get('TP2', 0):.2f}")

                # --- TELEGRAM RAPORLAMA ---
                st.write("---")
                if st.button("📤 Analizi Telegram'a Gönder", width='stretch'):
                    with st.spinner("🚀 Rapor hazırlanıyor ve gönderiliyor..."):
                        # Rapor Metni Hazırla
                        ml_target = ml_res['future_df']['Fiyat Tahmini'].iloc[-1] if 'ml_res' in locals() and 'future_df' in ml_res else "N/A"
                        
                        # Gemini Haber Özeti (İlk 2 haberin nedenini alalım)
                        news_summary = ""
                        if news_list:
                            news_summary = "\n".join([f"• *{n['category']}*: {n['reason']}" for n in news_list[:3]])
                        else:
                            news_summary = "• Son dönemde önemli haber akışı bulunmuyor."

                        report_text = f"""
📊 *{sym.upper()} Analiz Raporu*

💰 *Son Fiyat:* {live_px:.2f} ₺
🎯 *Hibrit Potansiyel:* %{final_score}
🛡️ *Güven Seviyesi:* {conv_label}
🏗️ *Güvenlik (PGS):* %{pgs_score}

🤖 *ML (5G) Hedef:* {ml_target if isinstance(ml_target, str) else f"{ml_target:.2f} ₺"}

🗞️ *AI Haber Analizi:*
{news_summary}

🚀 _Bist analiz robotu tarafından oluşturulmuştur_
"""
                        success = send_telegram_report(report_text)
                        if success:
                            st.success("✅ Rapor başarıyla Telegram'a gönderildi!")
                        else:
                            st.error("❌ Mesaj gönderilemedi. Lütfen secrets.toml ayarlarını kontrol edin.")
                
                if res.get('pgs', 100) < 50:
                    st.warning("⚠️ **Düşük Güvenlik Skoru:** Volatilite yüksek, risk yönetimine azami dikkat edin.")
                
                # ADX Bilgisi
                if 'ADX_14' in df.columns:
                    adx_val = df['ADX_14'].iloc[-1]
                    adx_status = "Güçlü 💪" if adx_val > 25 else "Zayıf ⚠️"
                    st.info(f"📈 **Trend Gücü (ADX):** {adx_val:.1f} ({adx_status})")
                
                # Destek & Direnç Tablosu
                if sr_data:
                    st.markdown("---")
                    st.subheader("🟢 En İyi Alım Bölgeleri (Destek)")
                    if sr_data.get('best_buy_zones'):
                        for label, val in sr_data['best_buy_zones']:
                            st.write(f"  ➡️ **{label}:** {val:.2f} ₺")
                    else:
                        st.write("Yakın destek bulunamadı.")
                    
                    st.subheader("🔴 En İyi Satım Bölgeleri (Direnç)")
                    if sr_data.get('best_sell_zones'):
                        for label, val in sr_data['best_sell_zones']:
                            st.write(f"  ➡️ **{label}:** {val:.2f} ₺")
                    else:
                        st.write("Yakın direnç bulunamadı.")
                    
                    with st.expander("📐 Fibonacci Seviyeleri"):
                        for name, val in sr_data.get('fibonacci', {}).items():
                            st.write(f"- **{name}:** {val:.2f} ₺")
                    
                    with st.expander("📊 Pivot Seviyeleri"):
                        pivots = sr_data.get('pivots', {})
                        for name, val in pivots.items():
                            st.write(f"- **{name}:** {val:.2f} ₺")

            with c2:
                fig = create_advanced_chart(df, sym.upper(), res['risk'], sr_data, sent_score)
                st.plotly_chart(fig, width='stretch')

    elif mode == "🔍 Piyasa Tarama Terminali (Screener)":
        st.title("🔍 Piyasa Tarama Terminali (Screener)")
        
        from screener import (get_sector_list, filter_by_sector, 
                              get_scan_history, get_persistent_signals,
                              add_to_watchlist, remove_from_watchlist, get_watchlist)
        import plotly.graph_objects as go
        
        # ---- SIDEBAR KONTROLLER ----
        scan_mode = st.sidebar.radio("Tarama Kapsamı", [
            "BIST 30 (Hızlı ~15sn)",
            "BIST 100 (~45sn)",
            "BIST Tüm Hisseler (~2dk)"
        ])
        
        if scan_mode.startswith("BIST 30"):
            selected_list = BIST30_SYMBOLS
            label = "BIST 30"
        elif scan_mode.startswith("BIST 100"):
            selected_list = BIST100_SYMBOLS
            label = "BIST 100"
        else:
            selected_list = BIST_ALL_SYMBOLS
            label = "BIST Tüm Hisseler"
        
        # Özellik 1: Sektör Filtresi
        sector_choice = st.sidebar.selectbox("🏭 Sektör Filtresi", get_sector_list())
        filtered_list = filter_by_sector(selected_list, sector_choice)
        
        # Özellik 4: Özel Filtre Oluşturucu
        st.sidebar.markdown("---")
        st.sidebar.subheader("🎛️ Özel Filtre")
        filter_option = st.sidebar.selectbox("Hazır Filtre", [
            "Tümünü Göster", "Sadece Güçlü Al", "Sadece Al", 
            "Sadece Sat / Güçlü Sat", "RSI < 30 (Aşırı Satım)", "RSI > 70 (Aşırı Alım)",
            "Hacim Patlaması Olanlar", "Dipten Dönüş Olanlar", "Çift AL (1D+1H) Teyitliler"
        ])
        
        # Piyasa Rejimi Göstergesi (BIST 100)
        xu100_df = fetch_data("XU100", "1d", "1y")
        market_regime = get_market_regime(xu100_df)
        st.sidebar.markdown("---")
        st.sidebar.subheader("📡 Piyasa Rejimi")
        
        regime_color = "red" if market_regime['is_bear'] else "green"
        regime_icon = "🛑" if market_regime['is_bear'] else "🚀"
        
        st.sidebar.markdown(f"""
            <div style="padding:10px; border-radius:5px; background-color: rgba(255,255,255,0.05); border: 1px solid {regime_color};">
                <span style="font-size:1.2rem;">{regime_icon} <b>{market_regime['mode']}</b></span><br>
                <small>XU100: {market_regime['daily_chg']}% | RSI: {market_regime['rsi']}</small>
            </div>
        """, unsafe_allow_html=True)

        custom_min_score = st.sidebar.slider("Min. V6 Hibrit Skor", 0, 100, 0)
        
        selected_fundamental_status = st.sidebar.multiselect(
            "🏷️ Temel Durum Filtresi",
            ["Kelepir 💎", "Emeklilik 🏖️", "Normal", "Balon ⚠️"],
            default=["Kelepir 💎", "Emeklilik 🏖️", "Normal", "Balon ⚠️"],
            help="Hisseleri temel analiz etiketlerine göre filtreleyin."
        )
        
        # Paralel iş parçacığı sayısı
        workers = st.sidebar.slider("⚡ Paralel İşçi Sayısı", 1, 10, 5)
        
        st.markdown(f"**{label}** kapsamında {'(Sektör: '+sector_choice+') ' if sector_choice != 'Tümü' else ''}"
                    f"**{len(filtered_list)}** hisse taranacak.")
        
        # ---- TARAMA BUTONU ----
        if st.button(f"🚀 {label} Taramasını Başlat", type="primary"):
            progress_bar = st.progress(0, text="Paralel tarama başlıyor...")
            screener_df = run_screener(filtered_list, current_user, progress_bar=progress_bar, max_workers=workers)
            progress_bar.empty()
            
            if not screener_df.empty:
                st.session_state['last_scan'] = screener_df
            else:
                st.error("Tarama sırasında sonuç üretilemedi.")
        
        # ---- SONUÇLARI GÖSTER ----
        if 'last_scan' in st.session_state and not st.session_state['last_scan'].empty:
            screener_df = st.session_state['last_scan'].copy()
            
            # Filtreleme uygula
            if filter_option == "Sadece Güçlü Al":
                screener_df = screener_df[screener_df['Piyasa Kararı'] == 'Güçlü Al']
            elif filter_option == "Sadece Al":
                screener_df = screener_df[screener_df['Piyasa Kararı'].isin(['Al', 'Güçlü Al'])]
            elif filter_option == "Sadece Sat / Güçlü Sat":
                screener_df = screener_df[screener_df['Piyasa Kararı'].str.contains('Sat')]
            elif filter_option == "RSI < 30 (Aşırı Satım)":
                screener_df = screener_df[screener_df['RSI'] != '-']
                screener_df = screener_df[screener_df['RSI'].astype(float) < 30]
            elif filter_option == "RSI > 70 (Aşırı Alım)":
                screener_df = screener_df[screener_df['RSI'] != '-']
                screener_df = screener_df[screener_df['RSI'].astype(float) > 70]
            elif filter_option == "Hacim Patlaması Olanlar":
                screener_df = screener_df[screener_df['Hacim Patlaması'] != '-']
            elif filter_option == "Dipten Dönüş Olanlar":
                screener_df = screener_df[screener_df['Dipten Dönüş'] != '-']
            elif filter_option == "Çift AL (1D+1H) Teyitliler":
                screener_df = screener_df[screener_df['1D+1H Uyum'].str.contains('Çift AL')]
            
            # Min skor filtresi
            if custom_min_score > 0:
                screener_df = screener_df[screener_df['V6 Hibrit Skor'] >= custom_min_score]
            
            # Temel durum filtresi
            if selected_fundamental_status:
                screener_df = screener_df[screener_df['Temel Durum'].isin(selected_fundamental_status)]
            
            if screener_df.empty:
                st.warning("Seçilen filtreye uyan hisse bulunamadı.")
            else:
                # ---- ÖZELLİK: Risk ve Getiri Matrisi ----
                st.markdown("---")
                st.subheader("📊 Stratejik Risk vs Yükseliş Potansiyeli Matrisi")
                fig_matrix = px.scatter(
                    screener_df, 
                    x="V6 Hibrit Skor", 
                    y="Güven Skoru (PGS)",
                    text="Hisse",
                    color="Değişim (%)",
                    size="Fiyat",
                    hover_data=["Piyasa Kararı", "ADX"],
                    title="Hisse Dağılım Matrisi (Büyüklük: Fiyat)",
                    template="plotly_dark",
                    color_continuous_scale="RdYlGn"
                )
                fig_matrix.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="Güven Sınırı")
                fig_matrix.add_vline(x=70, line_dash="dash", line_color="gray", annotation_text="Potansiyel Sınırı")
                st.plotly_chart(fig_matrix, width='stretch')
                # Özellik 6: Günün Yıldızı Kartları
                st.markdown("---")
                k1, k2, k3 = st.columns(3)
                top_score = screener_df.iloc[0]
                k1.metric("🥇 V6 Lideri", f"{top_score['Hisse']}", f"V6 Skor: {top_score['V6 Hibrit Skor']}")
                
                if 'Değişim (%)' in screener_df.columns:
                    best_gainer = screener_df.loc[screener_df['Değişim (%)'].idxmax()]
                    worst_loser = screener_df.loc[screener_df['Değişim (%)'].idxmin()]
                    k2.metric("📈 En Çok Yükselen", f"{best_gainer['Hisse']}", f"{float(best_gainer['Değişim (%)']):.2f}%")
                    k3.metric("📉 En Çok Düşen", f"{worst_loser['Hisse']}", f"{float(worst_loser['Değişim (%)']):.2f}%")
                
                st.markdown("---")
                
                # Renklendirme
                def style_all(row):
                    styles = [''] * len(row)
                    for i, col in enumerate(screener_df.columns):
                        val = row[col]
                        if col == 'Piyasa Kararı':
                            if 'Lideri' in str(val) or 'Güçlü Al' in str(val): styles[i] = 'background-color: #2d6a2e; color: white; font-weight: bold'
                            elif 'Trend' in str(val) or 'Al' in str(val): styles[i] = 'background-color: #1a5276; color: white'
                            elif 'Doygunluk' in str(val): styles[i] = 'background-color: #b7950b; color: black; font-weight: bold'
                            elif 'Freni' in str(val) or 'Güçlü Sat' in str(val): styles[i] = 'background-color: #641e16; color: white; font-weight: bold'
                            elif 'Potansiyeli' in str(val): styles[i] = 'background-color: #d35400; color: white; font-weight: bold'
                            elif 'Baskı' in str(val) or 'Sat' in str(val): styles[i] = 'background-color: #b03a2e; color: white'
                        elif col == 'V6 Hibrit Skor':
                            if val >= 70: styles[i] = 'color: #00ff00; font-weight: bold'
                            elif val < 40: styles[i] = 'color: #ff4c4c; font-weight: bold'
                        elif col == 'Temel Durum':
                            if 'Kelepir' in str(val): styles[i] = 'background-color: #0d5f30; color: white; font-weight: bold;'
                            elif 'Balon' in str(val): styles[i] = 'background-color: #8c1010; color: white; font-weight: bold;'
                            elif 'Emeklilik' in str(val): styles[i] = 'background-color: #1a5286; color: white; font-weight: bold;'
                        elif col == 'PD/DD':
                            if pd.notna(val) and float(val) > 0 and float(val) < 1.0: styles[i] = 'color: #00ff00;'
                            elif pd.notna(val) and float(val) > 10.0: styles[i] = 'color: #ff4c4c;'
                        elif col == 'F/K':
                            if pd.notna(val) and float(val) > 0 and float(val) < 10.0: styles[i] = 'color: #00ff00;'
                            elif pd.notna(val) and float(val) > 35.0: styles[i] = 'color: #ff4c4c;'
                        elif col == 'Güven Skoru (PGS)':
                            if val < 50: styles[i] = 'color: #ff4c4c; font-weight: bold'
                            elif val >= 80: styles[i] = 'color: #00ff00; font-weight: bold'
                        elif col == 'Graham Potansiyeli (%)':
                            try:
                                f_val = float(val) if pd.notna(val) else 0.0
                                if f_val > 30.0: styles[i] = 'background-color: #0b5345; color: #00ff00; font-weight: bold;'
                                elif f_val > 0.0: styles[i] = 'color: #00ff00;'
                                elif f_val < 0.0: styles[i] = 'color: #ff4c4c;'
                            except (ValueError, TypeError):
                                pass
                        elif col == 'Değişim (%)':
                            if isinstance(val, (int, float)):
                                if val > 0: styles[i] = 'color: #00ff00; font-weight: bold'
                                elif val < 0: styles[i] = 'color: #ff4c4c; font-weight: bold'
                        elif col == 'Disiplin':
                            if '✅' in str(val): styles[i] = 'color: #00ff00; font-weight: bold; text-align: center;'
                            elif '❌' in str(val): styles[i] = 'color: #ff4c4c; text-align: center;'
                        elif col == '1D+1H Uyum':
                            if 'Çift AL' in str(val): styles[i] = 'background-color: rgba(45, 106, 46, 0.4)'
                            elif 'Çift SAT' in str(val): styles[i] = 'background-color: rgba(146, 43, 33, 0.4)'
                        elif col == 'Hacim Skoru':
                            if isinstance(val, str) and 'Hacim Patlaması' in val: styles[i] = 'background-color: rgba(0, 102, 204, 0.4); font-weight: bold'
                        elif col == 'Dipten Dönüş':
                            if 'Dönüş' in str(val): styles[i] = 'background-color: rgba(204, 102, 0, 0.5); font-weight: bold'
                        elif col == 'Güven Seviyesi':
                            if 'YÜKSEK' in str(val): styles[i] = 'background-color: #0b5345; color: white; font-weight: bold'
                            elif 'DÜŞÜK' in str(val): styles[i] = 'color: #ff4c4c;'
                        elif col == 'ADX':
                            if 'Güçlü' in str(val): styles[i] = 'color: #00ff00; font-weight: bold'
                        elif col == 'Zirve Uzaklığı':
                            num_val = float(str(val).replace('%','')) if '%' in str(val) else 0
                            if num_val > 5: styles[i] = 'color: #ff4c4c;' # Tepeden %5+ satış yemişse
                    return styles
                
                st.success(f"Toplam {len(screener_df)} hisse listelendi.")
                
                # Checkbox kolonu ekle
                if "Seç" not in screener_df.columns:
                    screener_df.insert(0, "Seç", False)
                
                # Etkileşimli Tablo (Sadece 'Seç' kolonu değiştirilebilir)
                edited_df = st.data_editor(
                    screener_df.style.apply(style_all, axis=1).format(precision=2),
                    column_config={
                        "Seç": st.column_config.CheckboxColumn("Seç", default=False)
                    },
                    disabled=[col for col in screener_df.columns if col != "Seç"],
                    hide_index=True,
                    width='stretch',
                    height=600,
                    key="screener_editor"
                )
                
                # Seçilen hisseleri filtrele
                # Not: edited_df bir styler nesnesi değil DataFrame olarak döner.
                selected_rows = edited_df[edited_df["Seç"] == True]
                
                if not selected_rows.empty:
                    st.write(f"✅ {len(selected_rows)} hisse seçildi.")
                    
                    with st.expander("📥 Seçilenleri Portföye Ekle", expanded=True):
                        adet = st.number_input("Varsayılan Adet", min_value=1.0, value=100.0)
                        if st.button("Hepsini Ekle", type="primary"):
                            for _, row in selected_rows.iterrows():
                                ticker = row['Hisse']
                                fiyat = float(row['Fiyat']) if 'Fiyat' in row else 1.0
                                pf.alis_yap(current_user, ticker, adet, fiyat, not_text="Screener üzerinden eklendi.")
                            st.success("Seçilen tüm hisseler portföyünüze eklendi!")
                
                # Özellik 3: CSV Export
                csv_data = screener_df.drop(columns=["Seç"]).to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Sonuçları CSV Olarak İndir", csv_data, "tarama_sonuclari.csv", "text/csv", width='stretch')
                
                # Özellik 5: Hızlı Grafik Önizleme
                st.markdown("---")
                st.subheader("📈 Hızlı Grafik Önizleme")
                chart_sym = st.selectbox("Grafiğini görmek istediğiniz hisse:", screener_df['Hisse'].tolist())
                if chart_sym:
                    with st.spinner(f"{chart_sym} grafiği çiziliyor..."):
                        qdf = fetch_data(chart_sym, "1d", "3mo")
                        if not qdf.empty:
                            qdf = calculate_indicators(qdf)
                            fig_q = go.Figure()
                            fig_q.add_trace(go.Candlestick(x=qdf.index, open=qdf['Open'], high=qdf['High'], low=qdf['Low'], close=qdf['Close'], name='Fiyat'))
                            if 'SMA_20' in qdf.columns:
                                fig_q.add_trace(go.Scatter(x=qdf.index, y=qdf['SMA_20'], line=dict(color='orange', width=1), name='SMA 20'))
                            if 'SMA_50' in qdf.columns:
                                fig_q.add_trace(go.Scatter(x=qdf.index, y=qdf['SMA_50'], line=dict(color='cyan', width=1), name='SMA 50'))
                            fig_q.update_layout(template='plotly_dark', height=400, xaxis_rangeslider_visible=False,
                                                title=f"{chart_sym} - Son 3 Ay Mum Grafiği")
                            st.plotly_chart(fig_q, width='stretch')
                            
                            # RSI paneli
                            if 'RSI_14' in qdf.columns:
                                fig_rsi = go.Figure()
                                fig_rsi.add_trace(go.Scatter(x=qdf.index, y=qdf['RSI_14'], line=dict(color='magenta'), name='RSI 14'))
                                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Aşırı Alım")
                                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Aşırı Satım")
                                fig_rsi.update_layout(template='plotly_dark', height=200, title="RSI (14)")
                                st.plotly_chart(fig_rsi, width='stretch')
                
                # Özellik 8: Watchlist'e Ekleme
                st.markdown("---")
                st.subheader("🔔 İzleme Listesine Ekle")
                wl_col1, wl_col2 = st.columns([2, 1])
                with wl_col1:
                    wl_sym = st.selectbox("Hisse Seç:", screener_df['Hisse'].tolist(), key="wl_add")
                with wl_col2:
                    wl_note = st.text_input("Not:", "", key="wl_note")
                if st.button("➕ İzleme Listesine Ekle"):
                    add_to_watchlist(current_user, wl_sym, wl_note)
                    st.success(f"{wl_sym} izleme listesine eklendi!")
        
        # ---- TARAMA GEÇMİŞİ (Özellik 2) ----
        st.markdown("---")
        with st.expander("📊 Tarama Geçmişi & Tutarlı Sinyaller"):
            persistent_df = get_persistent_signals(current_user, min_days=2)
            if not persistent_df.empty:
                st.write("**🔁 Ardışık Günlerde Aynı Yönde Sinyal Veren Hisseler:**")
                st.dataframe(persistent_df.style.format(precision=2), width='stretch')
            else:
                st.info("Henüz birden fazla gün tarama geçmişi oluşmamış. Her gün tarama yaparak tutarlı sinyalleri burada göreceksiniz.")
        
        # ---- WATCHLIST (Özellik 8) ----
        with st.expander("🔔 İzleme Listem (Watchlist)"):
            wl_df = get_watchlist(current_user)
            if not wl_df.empty:
                st.dataframe(wl_df.style.format(precision=2), width='stretch')
                wl_del = st.selectbox("Çıkarılacak Hisse:", wl_df['ticker'].tolist(), key="wl_del")
                if st.button("🗑️ İzleme Listesinden Çıkar"):
                    remove_from_watchlist(current_user, wl_del)
                    st.success(f"{wl_del} listeden çıkarıldı!")
                    st.rerun()
            else:
                st.info("İzleme listeniz boş. Tarama sonuçlarından hisse ekleyebilirsiniz.")
        
        # ---- SCREENER TERİMLERİ SÖZLÜĞÜ (YENİ) ----
        st.markdown("---")
        with st.expander("📚 Screener Terimleri ve Anlamları", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                **💎 Kelepir:** PD/DD oranı 1.1'in, F/K 10'un altında olan, defter değerine yakın veya altında işlem gören çok ucuz hisseler.
                **🏖️ Emeklilik:** Temettü verimi %5 ve üzeri olan, yatırımcısına düzenli nakit akışı sağlamayı hedefleyen köklü şirketler.
                **🚀 Pozitif Trend (V6):** Hem teknik (indikatörler) hem temel verileri harmanlayan V6 skoru 65 ve üzeri olan yükseliş potansiyelli hisseler.
                """)
            with col2:
                st.markdown("""
                **⚠️ Balon:** F/K oranı 35'in veya PD/DD 10'un üzerine çıkmış, temellerinden çok uzaklaşmış, düzeltme riski yüksek hisseler.
                **⚖️ V6 Hibrit Skor:** %60 Teknik Momentum ve %40 Temel Analiz verilerinin melez bir algoritma ile hesaplanmış final puanıdır.
                **🛡️ Güven Skoru (PGS):** Sinyalin volatilitesi ve indikatör uyumuna göre hesaplanan tutarlılık puanıdır (Yüksek = Güvenli).
                """)

        st.warning("⚠️ **Yasal Uyarı:** Bu sonuçlar teknik ve istatistiksel analize dayanmaktadır. Kesinlikle yatırım tavsiyesi niteliği taşımaz.")


    elif mode == "🤖 Öngörüsel Model Analizi (Predictive Engine)":
        st.title("🤖 Öngörüsel Model Analizi (Predictive Engine)")
        sym = st.sidebar.text_input("Hisse Kodu (Örn: EREGL)", "ASELS")
        days = st.sidebar.slider("Gelecek Tahmin Süresi (Gün)", 5, 60, 30)
        
        if sym:
            with st.status(f"🤖 **Robot Yapay Zeka** {sym} için tahmin motorunu çalıştırıyor...", expanded=True) as status:
                df_long = fetch_data(sym, "1d", "3y")
                if df_long.empty:
                    st.error("Veri bulunamadı.")
                    status.update(label="❌ Tahmin başarısız.", state="error")
                    return
                
                df_long = calculate_indicators(df_long)
                ml_res = generate_ml_forecast(df_long, days_ahead=days)
                status.update(label="✅ Robot Yapay Zeka analizi tamamladı.", state="complete")

            with st.expander("🤖 Robot Yapay Zeka - Genişleyen Huni (Cone) Tahmin Modeli", expanded=True):
                if "error" in ml_res:
                    st.warning(ml_res["error"])
                else:
                    # ML Uyarılarını (Makro Veri Onayları) Göster
                    if ml_res.get('warnings'):
                        for w in ml_res['warnings']:
                            st.warning(w)
                    else:
                        st.success("✅ Hibrit Onay: Endeks ve Kur verileri modellemeye başarıyla dahil edildi.")

                    c_ml1, c_ml2 = st.columns([3, 1])
                    with c_ml1:
                        fig_ml = create_ml_chart(df_long, ml_res, sym)
                        st.plotly_chart(fig_ml, width='stretch')
                    with c_ml2:
                        st.metric("Model Başarı Skoru (R²)", f"%{ml_res['confidence_score']}")
                        
                        last_est = ml_res['future_df']['Fiyat Tahmini'].iloc[-1]
                        current_px = df_long['Close'].iloc[-1]
                        est_diff = ((last_est - current_px) / current_px) * 100
                        st.metric(f"{days}G Hedef Projeksiyon", f"{last_est:.2f} ₺", f"{est_diff:+.1f}%")
                        
                        st.write("**Stratejik Not:**")
                        st.caption("Bu model, Random Forest mimarisi kullanarak geçmiş volatiliteyi 'Genişleyen Huni' grafiğine yansıtır. Vade uzadıkça belirsizlik (huni genişliği) istatistiksel olarak artar.")
                
                # --- OTONOM HİBRİT ALARM (V5) KONTROLÜ ---
                try:
                    # Global kütüphaneler kullanılacak
                    xu100_temp = fetch_data("XU100", "1d", "1mo")
                    regime_temp = get_market_regime(xu100_temp)
                    sent_val, _ = get_sentiment_summary(sym)
                    sig_res = generate_signals_and_score(df_long, market_regime=regime_temp, sentiment_score=sent_val)
                    
                    if check_hybrid_alerts(sym, sig_res.get('score', 0), current_px, sent_val, last_est):
                        st.success("🚨 **Hibrit Algoritma Uyarıyor:** Bu hisse Otonom Trading (V5) algoritmamızın tüm Perfect Setup kriterlerini (+80 Puan, Pozitif AI Haber Akışı, Yüksek ML Hedefi) başarıyla karşılıyor. Telegram acil durum bildirimi gönderildi!")
                except Exception as e:
                    pass

                st.info("💡 **Huni Okuma Kılavuzu:** İç halka %68 (1 SD), dış halka %95 (2 SD) olasılık kümesini temsil eder. Fiyatın huni içinde kalma olasılığı istatistiksel olarak yüksektir.")

    elif mode == "💼 Gelişmiş Backtest":
        st.title("💼 Kurumsal Portföy Backtest Simülatörü")
        sym = st.sidebar.text_input("Hisse Kodu (Örn: EREGL)", "KCHOL")
        capital = st.sidebar.number_input("Başlangıç Sermayesi (₺)", min_value=1000, value=100000)
        comms = st.sidebar.number_input("İşlem Başına Komisyon (%)", min_value=0.0, value=0.2, step=0.1) / 100
        period_days = st.sidebar.slider("Geçmiş Gözlem Süresi (Gün)", 90, 500, 180)
        
        if st.button("Backtest'i Başlat"):
            with st.spinner("Simülasyon hesaplanıyor..."):
                df = fetch_data(sym, "1d", "5y")
                res = run_advanced_backtest(df, initial_capital=capital, commission_rate=comms, lookback_days=period_days)
            
            if "error" in res:
                st.error(res["error"])
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Nihai Portföy Değeri", f"₺{res['final_equity']:,.2f}", f"{res['total_return_pct']:.2f}%")
                c2.metric("Toplam İşlem Sayısı", f"{res['number_of_trades']}")
                c3.metric("Maksimum Kayıp (Drawdown)", f"{res['max_drawdown_pct']:.2f}%", delta_color="inverse")
                c4.metric("Al&Tut (Buy-Hold) Getirisi", f"{res['buy_and_hold_return_pct']:.2f}%")
                
                st.plotly_chart(create_equity_curve_chart(res['equity_curve'], sym.upper()), width='stretch')
                
                with st.expander("Detaylı İşlem Dökümü (Trades)"):
                    if res['trades']:
                        st.table(pd.DataFrame(res['trades']).style.format(precision=2))
                    else:
                        st.write("Belirtilen süre zarfında AL/SAT sinyali üretilmedi.")

    elif mode == "📈 Sanal Portföy":
        st.title("📈 Sanal Portföy Yönetimi")
        st.markdown("Beğendiğiniz hisseleri sanal olarak alıp, zaman içindeki başarınızı takip edebilirsiniz.")

        with st.expander("➕ Yeni Alım Ekle"):
            c1, c2, c3 = st.columns(3)
            with c1:
                t_sym = st.text_input("Hisse Kodu", "EREGL").upper()
            
            # Dinamik Fiyat Yakalama ve Doğrulama
            oto_fiyat = 0.0
            is_valid_ticker = False
            if t_sym:
                lv = get_live_price(t_sym)
                if lv > 0:
                    oto_fiyat = lv
                    is_valid_ticker = True
                else:
                    st.error(f"⚠️ '{t_sym}' kodu piyasada bulunamadı. Sahte/Yanlış bir kod girmiş olabilirsiniz.")

            with c2:
                t_adet = st.number_input("Adet", min_value=0.1, value=10.0)
            with c3:
                t_fiyat = st.number_input("Alış Fiyatı (₺)", min_value=0.0, value=float(oto_fiyat))
                
            t_not = st.text_area("Not (Opsiyonel)", "")
            
            if st.button("Portföye Ekle"):
                if not is_valid_ticker:
                    st.warning("Piyasada olmayan veya teyit edilemeyen bir hisseyi ekleyemezsiniz.")
                else:
                    # Otonom Risk Parametrelerini Hesapla (ATR bazlı dinamik SL/TP)
                    sl_val, tp_val, var_val = None, None, None
                    try:
                        df_risk = fetch_data(t_sym, "1d", "6mo")
                        if not df_risk.empty and len(df_risk) > 20:
                            ind_res = calculate_indicators(df_risk)
                            atr = ind_res['ATR'].iloc[-1]
                            sl_val = round(float(t_fiyat) - (atr * 1.5), 2) # Risk Katsayısı: 1.5X ATR
                            tp_val = round(float(t_fiyat) + (atr * 3.0), 2) # Ödül Katsayısı: 3.0X ATR
                            var_val = round((float(t_fiyat) - sl_val) * float(t_adet), 2) # VaR: Total Riskteki Sermaye
                    except Exception:
                        pass
                        
                    pf.alis_yap(current_user, t_sym, t_adet, t_fiyat, t_not, sl_val, tp_val, var_val)
                    st.success(f"{t_sym} portföye eklendi! (Otomatik SL: {sl_val} ₺, TP: {tp_val} ₺)")
                    st.rerun()

        # Açık Pozisyonlar
        c_hdr1, c_hdr2 = st.columns([3, 1])
        with c_hdr1:
            st.subheader("🏁 Açık Pozisyonlar")
        with c_hdr2:
            if st.button("🔄 Canlı Fiyatları Yenile", width='stretch'):
                st.rerun()

        acik_df = pf.acik_pozisyonlar(current_user)
        
        if not acik_df.empty:
            p_data = []
            with st.spinner("Anlık fiyatlar piyasadan çekiliyor..."):
                for idx, row in acik_df.iterrows():
                    # Gerçek zamanlı (1 dakikalık gecikmeli) güncel fiyatı çek
                    curr_price = get_live_price(row['ticker'])
                    if curr_price == 0.0: # Fiyat bulunamadıysa veritabanından yedek olarak çek
                        df_curr = fetch_data(row['ticker'], "1d", "5d")
                        curr_price = df_curr['Close'].iloc[-1] if not df_curr.empty else 0
                
                    maliyet = row['adet'] * row['alis_fiyati']
                    guncel_deger = row['adet'] * curr_price
                    kar_zarar = guncel_deger - maliyet
                    kz_yuzde = (kar_zarar / maliyet) * 100 if maliyet > 0 else 0
                    
                    # Risk durumunu hesapla
                    sl_text = f"{row.get('sl', 0):.2f}" if pd.notna(row.get('sl')) else "Yok"
                    tp_text = f"{row.get('tp', 0):.2f}" if pd.notna(row.get('tp')) else "Yok"
                    var_text = f"{row.get('var', 0):.2f}" if pd.notna(row.get('var')) else "Yok"
                    
                    p_data.append({
                        "ID": row['id'],
                        "Hisse": row['ticker'],
                        "Adet": row['adet'],
                        "Maliyet (₺)": round(row['alis_fiyati'], 2),
                        "Güncel (₺)": round(curr_price, 2),
                        "Stop-Loss": sl_text,
                        "Take-Profit": tp_text,
                        "Risk (VaR) ₺": var_text,
                        "Kâr/Zarar (₺)": round(kar_zarar, 2),
                        "Değişim (%)": round(kz_yuzde, 2),
                        "Tarih": row['alis_tarihi']
                    })
            
            p_df = pd.DataFrame(p_data)
            
            # Tablo gösterimi
            def highlight_pnl(val):
                if isinstance(val, (int, float)):
                    color = 'green' if val > 0 else 'red'
                    return f'color: {color}'
                return ''
            
            try:
                # Pandas 2.1+ için .map, eski sürümler için .applymap (fallback)
                if hasattr(p_df.style, 'map'):
                    styled_p_df = p_df.style.map(highlight_pnl, subset=['Kâr/Zarar (₺)', 'Değişim (%)'])
                else:
                    styled_p_df = p_df.style.applymap(highlight_pnl, subset=['Kâr/Zarar (₺)', 'Değişim (%)'])
            except Exception:
                styled_p_df = p_df # Hata durumunda stil olmadan göster

            st.dataframe(styled_p_df.format(precision=2) if hasattr(styled_p_df, 'format') else styled_p_df, width='stretch')
            
            # Toplam Durum
            toplam_maliyet = sum(d['Adet'] * d['Maliyet (₺)'] for d in p_data)
            toplam_guncel = sum(d['Adet'] * d['Güncel (₺)'] for d in p_data)
            toplam_kz = toplam_guncel - toplam_maliyet
            toplam_yuzde = (toplam_kz / toplam_maliyet) * 100 if toplam_maliyet > 0 else 0
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Toplam Yatırım", f"₺{toplam_maliyet:,.2f}")
            mc2.metric("Portföy Değeri", f"₺{toplam_guncel:,.2f}")
            mc3.metric("Net Kâr/Zarar", f"₺{toplam_kz:,.2f}", f"{toplam_yuzde:.2f}%")

            # Görsel Grafikler
            st.markdown("---")
            gc1, gc2 = st.columns(2)
            
            with gc1:
                st.subheader("🍕 Portföy Dağılımı")
                fig_pie = px.pie(p_df, values='Adet', names='Hisse', title='Hisse Dağılımı (Adet Bazlı)', hole=0.4, template='plotly_dark')
                st.plotly_chart(fig_pie, width='stretch')
            
            with gc2:
                st.subheader("📊 Hisse Bazlı Kar/Zarar")
                p_df_sorted = p_df.sort_values('Kâr/Zarar (₺)', ascending=False)
                fig_bar = px.bar(p_df_sorted, x='Hisse', y='Kâr/Zarar (₺)', color='Değişim (%)',
                                 title='Hisse Bazlı Kazanç Durumu', template='plotly_dark',
                                 color_continuous_scale=['red', 'yellow', 'green'],
                                 color_continuous_midpoint=0)
                st.plotly_chart(fig_bar, width='stretch')

            # İşlem Kapatma
            st.markdown("---")
            with st.expander("🛑 İşlemi Kapat (Sat) / Hatalı Kaydı Sil"):
                trade_to_close = st.selectbox("Kapatılacak İşlem ID", p_df['ID'].tolist())
                # Seçilen işlemin güncel fiyatını varsayılan yap (0.0 hatasını engelle)
                current_p = p_df[p_df['ID']==trade_to_close]['Güncel (₺)'].iloc[0]
                satis_px = st.number_input("Satış Fiyatı (₺)", min_value=0.01, value=max(0.01, float(current_p)))
                if st.button("İşlemi Kapat / Sil"):
                    pf.satis_yap(trade_to_close, satis_px)
                    st.success("İşlem kapatıldı!")
                    st.rerun()
        else:
            st.info("Henüz açık pozisyonunuz bulunmuyor.")

        # Geçmiş İşlemler
        st.subheader("📜 Geçmiş İşlemler")
        kapali_df = pf.kapali_pozisyonlar(current_user)
        if not kapali_df.empty:
            st.dataframe(kapali_df.style.format(precision=2), width='stretch')
            
            with st.expander("🗑️ Geçmiş İşlemi Veritabanından Sil"):
                del_id = st.selectbox("Silinecek İşlem ID", kapali_df['id'].tolist(), key="del_kapali")
                if st.button("Kalıcı Olarak Sil"):
                    pf.islemi_sil(del_id)
                    st.success("İşlem başarıyla silindi!")
                    st.rerun()
        else:
            st.write("Kapatılmış işlem bulunmuyor.")

    elif mode == "📰 KAP ve Haberler":
        render_kap_news_panel()

    elif mode == "🏆 Stratejik Seçki (Top Picks)":
        st.title("🏆 Stratejik Seçki (Top Picks) - Pro Terminal")
        st.markdown("""
        Bu modül, seçtiğiniz hisse havuzundaki tüm hisseleri **8 farklı boyutta** derinlemesine analiz eder:
        - 📊 Teknik İndikatörler (RSI, MACD, SMA, EMA vb.)
        - 📈 Momentum Trendi
        - 🌊 Hacim Patlaması
        - ⏰ Çoklu Zaman Dilimi Teyidi (1D + 1H)
        - 🕯️ Mum Formasyonları
        - 🛡️ Destek/Direnç Yakınlığı
        - 📰 Haber Duygu Analizi (Sentiment)
        - 🔥 Dipten Dönüş Sinyali
        
        Tüm bu faktörler ağırlıklı bir **Kompozit Skor** ile birleştirilerek **önümüzdeki 1 hafta** içinde yükselme ihtimali en yüksek **ilk 5 hisse** sunulur.
        
        *💡 Ayı piyasasında sistem, momentum kovalayan hisseler yerine 'Aşırı Satım' sonrası 'Dipten Dönüş' formasyonu gösteren sağlam kağıtlara öncelik verir.*
        """)
        
        pick_scope = st.sidebar.radio("🎯 Analiz Kapsamı", [
            "BIST 30 (Hızlı ~1dk)",
            "BIST 100 (Detaylı ~3dk)",
            "BIST Tüm Hisseler (Uzun ~10dk)"
        ], key="pick_scope")
        
        top_n = st.sidebar.slider("🏅 Kaç hisse önerilsin?", 3, 10, 5)
        
        if pick_scope.startswith("BIST 30"):
            pick_list = BIST30_SYMBOLS
            pick_label = "BIST 30"
        elif pick_scope.startswith("BIST 100"):
            pick_list = BIST100_SYMBOLS
            pick_label = "BIST 100"
        else:
            pick_list = BIST_ALL_SYMBOLS
            pick_label = "BIST Tüm Hisseler"
        
        if st.button(f"🔬 {pick_label} Derin Analizi Başlat", type="primary"):
            progress_bar = st.progress(0, text="Derin analiz başlıyor...")
            top_results = find_top_picks(pick_list, top_n=top_n, progress_bar=progress_bar)
            progress_bar.empty()
            
            if top_results:
                st.session_state['top_picks'] = top_results
                # Otomatik kaydet
                save_top_picks_history(current_user, top_results)
                st.success("Analiz tamamlandı ve geçmişe kaydedildi!")
        
        # ---- GEÇMİŞ KAYITLAR (Özellik 10) ----
        st.sidebar.markdown("---")
        show_history = st.sidebar.checkbox("📂 Geçmiş Analizleri Göster", key="show_picks_history")
        
        if show_history:
            history_dates = get_top_picks_history_dates(current_user)
            if history_dates:
                selected_date = st.sidebar.selectbox("Tarih Seçin:", history_dates)
                if selected_date:
                    hist_results = get_top_picks_by_date(current_user, selected_date)
                    if hist_results:
                        st.session_state['top_picks'] = hist_results
                        st.sidebar.success(f"{selected_date} verileri yüklendi.")
            else:
                st.sidebar.info("Henüz kayıtlı analiz bulunmuyor.")

        if 'top_picks' in st.session_state and st.session_state['top_picks']:
            top_results = st.session_state['top_picks']
            
            st.markdown("---")
            run_info = f" (Yüklenen Tarih: {selected_date})" if show_history and 'selected_date' in locals() else ""
            st.subheader(f"🏆 Haftalık Yükselme Potansiyeli En Yüksek {len(top_results)} Hisse{run_info}")
            
            summary_data = []
            for r in top_results:
                summary_data.append({
                    "Hisse": r.get('ticker', 'N/A'),
                    "Sektör": r.get('sektor', 'N/A'),
                    "Fiyat (₺)": r.get('fiyat', 0),
                    "🏆 V6 Hibrit Skor": r.get('kompozit_skor', 0),
                    "F/K": r.get('pe', 0),
                    "PD/DD": r.get('pb', 0),
                    "Temel Durum": r.get('temel_durum', 'Normal'),
                    "🛡️ Güven Skoru (PGS)": r.get('pgs', 50),
                    "Karar": r.get('karar', 'N/A'),
                    "Haber Algısı": f"%{r.get('news_sentiment', 0)}"
                })
            
            sum_df = pd.DataFrame(summary_data)
            
            def style_picks(row):
                styles = [''] * len(row)
                for i, col in enumerate(sum_df.columns):
                    val = row[col]
                    if col == '🏆 V6 Hibrit Skor':
                        if val >= 70: styles[i] = 'background-color: #2d6a2e; color: white; font-weight: bold'
                        elif val >= 55: styles[i] = 'background-color: #1a5276; color: white'
                    elif col == '🛡️ Güven Skoru (PGS)':
                        if val >= 80: styles[i] = 'color: #00ff00; font-weight: bold'
                        elif val < 50: styles[i] = 'color: #ff4c4c; font-weight: bold'
                    elif col == 'Temel Durum':
                        if 'Kelepir' in str(val): styles[i] = 'background-color: #0d5f30; color: white; font-weight: bold;'
                        elif 'Balon' in str(val): styles[i] = 'background-color: #8c1010; color: white; font-weight: bold;'
                        elif 'Emeklilik' in str(val): styles[i] = 'background-color: #1a5286; color: white; font-weight: bold;'
                    elif col == 'Karar':
                        if 'Trend' in str(val) or 'Lideri' in str(val): styles[i] = 'color: #00ff00; font-weight: bold'
                        elif 'Baskı' in str(val) or 'Riskli' in str(val): styles[i] = 'color: #ff4c4c; font-weight: bold'
                return styles
            
            if "Seç" not in sum_df.columns:
                sum_df.insert(0, "Seç", False)
                
            edited_sum_df = st.data_editor(
                sum_df.style.apply(style_picks, axis=1).format(precision=2),
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Seç", default=False)
                },
                disabled=[col for col in sum_df.columns if col != "Seç"],
                hide_index=True,
                width='stretch',
                key="toppicks_editor"
            )
            
            selected_picks = edited_sum_df[edited_sum_df["Seç"] == True]
            if not selected_picks.empty:
                st.write(f"✅ {len(selected_picks)} hisse seçildi.")
                with st.expander("📥 Seçilenleri Portföye Ekle", expanded=True):
                    adet = st.number_input("Varsayılan Adet", min_value=1.0, value=100.0, key="tp_adet")
                    if st.button("Hepsini Ekle", type="primary", key="tp_ekle"):
                        for _, row in selected_picks.iterrows():
                            ticker = row['Hisse']
                            fiyat = float(row['Fiyat (₺)']) if 'Fiyat (₺)' in row else 1.0
                            pf.alis_yap(current_user, ticker, adet, fiyat, not_text="Top Picks üzerinden eklendi.")
                        st.success("Seçilen hisseler portföyünüze eklendi!")
            
            # --- TELEGRAM TOP PICKS RAPORU ---
            if st.button("📤 Haftalık Listeyi Telegram'a Gönder", width='stretch'):
                with st.spinner("🚀 Haftalık rapor hazırlanıyor..."):
                    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                    report_lines = [f"🏆 *Haftalık Yükselme Potansiyeli En Yüksek {len(top_results)} Hisse* \n"]
                    
                    for i, r in enumerate(top_results):
                        medal = medals[i] if i < 10 else f"{i+1}."
                        ticker = r.get('ticker', 'N/A')
                        skor = r.get('kompozit_skor', 0)
                        fiyat = r.get('fiyat', 0)
                        karar = r.get('karar', 'N/A')
                        
                        line = f"{medal} *{ticker}* \n🎯 Skor: %{skor} | 💰 {fiyat:.2f} ₺ \n⚖️ Karar: {karar}\n"
                        report_lines.append(line)
                    
                    report_lines.append("\n🚀 _Bist analiz robotu tarafından oluşturulmuştur_")
                    report_text = "\n".join(report_lines)
                    
                    success = send_telegram_report(report_text)
                    if success:
                        st.success("✅ Haftalık liste Telegram'a gönderildi!")
                    else:
                        st.error("❌ Gönderim başarısız.")

            st.markdown("---")
            st.subheader("🔬 Detaylı Hisse Analizleri")
            
            import plotly.graph_objects as go
            for rank, pick in enumerate(top_results, 1):
                medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][rank-1] if rank <= 10 else f"{rank}."
                p_ticker = pick.get('ticker', 'N/A')
                p_potansiyel = pick.get('kompozit_skor', 0)
                p_pgs = pick.get('pgs', 50)
                p_fiyat = pick.get('fiyat', 0)
                
                with st.expander(f"{medal} #{rank} - {p_ticker} | V6 Hibrit Skor: {p_potansiyel} | Güven (PGS): {p_pgs} | {p_fiyat}₺", expanded=(rank <= 3)):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("🏆 V6 Hibrit Skor", f"{p_potansiyel}/100")
                    m2.metric("🛡️ Güvenlik (PGS)", f"{p_pgs}/100")
                    m3.metric("F/K", pick.get('pe', '-'))
                    m4.metric("PD/DD", pick.get('pb', '-'))
                    
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**🏛️ Temel Not:** {pick.get('temel_skor', 50)}")
                    c2.write(f"**📈 Teknik Skor:** {pick.get('teknik_skor', 50)}")
                    
                    g_val_disp = pick.get('graham_value', 'N/A')
                    if isinstance(g_val_disp, (int, float)) and g_val_disp > 0:
                        c3.write(f"**💎 Graham Adil Değer:** {g_val_disp:.2f} ₺")
                    else:
                        c3.write(f"**💎 Graham Adil Değer:** {g_val_disp}")
                    
                    st.markdown("---")
                    st.write("**⚙️ Hibrit Skor Hesaplaması:**")
                    v6_data = {
                        "Modül": ["📊 Teknik Analiz Kompozit", "🏛️ Temel Analiz Notu"],
                        "Ağırlık": ["%60", "%40"],
                        "Ham Skor": [pick.get('teknik_skor', 50), pick.get('temel_skor', 50)]
                    }
                    st.table(pd.DataFrame(v6_data))
                    
                    st.markdown("---")
                    st.write("**⚙️ Teknik Detaylar (Bonus Puanlar):**")
                    comp_data = {
                        "Bileşen": ["📈 Momentum", "🌊 Hacim", "⏰ Çoklu TF", "🕯️ Formasyon", "🛡️ Destek", "📰 Haber", "🔥 Dipten Dönüş"],
                        "Bonus Puan": [
                            f"+{pick['momentum_bonus']}",
                            f"+{pick['volume_bonus']}",
                            f"+{pick['tf_bonus']}",
                            f"+{pick['pattern_bonus']}",
                            f"+{pick['support_bonus']}",
                            f"+{pick['news_bonus']} (Duygu: %{pick['news_sentiment']})",
                            f"+{pick['reversal_bonus']}"
                        ]
                    }
                    st.dataframe(pd.DataFrame(comp_data), width='stretch', hide_index=True)
                    
                    st.markdown("---")
                    r1, r2, r3 = st.columns(3)
                    risk = pick.get('risk_details', {})
                    sl_val = risk.get('SL', '-')
                    tp_val = risk.get('TP1', '-')
                    r1.metric("Stop Loss", f"{sl_val:.2f}₺" if isinstance(sl_val, (int, float)) else f"{sl_val}₺")
                    r2.metric("Take Profit 1", f"{tp_val:.2f}₺" if isinstance(tp_val, (int, float)) else f"{tp_val}₺")
                    r3_val = pick['dist_support_pct']
                    r3.metric("Desteğe Uzaklık", f"%{float(r3_val):.2f}" if isinstance(r3_val, (int, float)) or (isinstance(r3_val, str) and r3_val.replace('.','',1).isdigit()) else f"%{r3_val}")
                    
                    s1, s2 = st.columns(2)
                    with s1:
                        st.write("**🕯️ Mum Formasyonu:**")
                        st.write(pick['pattern_text'])
                        st.write(f"**🔥 Dipten Dönüş:** {pick['reversal']}")
                    with s2:
                        res_dist = pick['dist_resist_pct']
                        st.write(f"**Dirençe Uzaklık:** %{float(res_dist):.2f}" if isinstance(res_dist, (int, float)) or (isinstance(res_dist, str) and res_dist.replace('.','',1).isdigit()) else f"**Dirençe Uzaklık:** %{res_dist}")
                        st.write(f"**Sektör:** {pick['sektor']}")
                    
                    if pick['news_headlines']:
                        st.markdown("---")
                        st.write("**📰 Son Haberler:**")
                        for hl in pick['news_headlines']:
                            st.write(f"  • {hl}")
                    
                    st.markdown("---")
                    with st.spinner("Grafik çiziliyor..."):
                        qdf = fetch_data(pick['ticker'], "1d", "3mo")
                        if not qdf.empty:
                            qdf = calculate_indicators(qdf)
                            fig = go.Figure()
                            fig.add_trace(go.Candlestick(x=qdf.index, open=qdf['Open'], high=qdf['High'], low=qdf['Low'], close=qdf['Close'], name='Fiyat'))
                            if 'SMA_20' in qdf.columns:
                                fig.add_trace(go.Scatter(x=qdf.index, y=qdf['SMA_20'], line=dict(color='orange', width=1), name='SMA 20'))
                            if 'SMA_50' in qdf.columns:
                                fig.add_trace(go.Scatter(x=qdf.index, y=qdf['SMA_50'], line=dict(color='cyan', width=1), name='SMA 50'))
                            fig.update_layout(template='plotly_dark', height=350, xaxis_rangeslider_visible=False, title=f"{pick['ticker']} - Son 3 Ay")
                            st.plotly_chart(fig, width='stretch')
            
            st.markdown("---")
            st.warning("⚠️ **Yasal Uyarı:** Bu sonuçlar teknik ve istatistiksel analize dayanmaktadır. Kesinlikle yatırım tavsiyesi niteliği taşımaz.")

    elif mode == "🌟 Haber Alpha (Alpha Discovery)":
        st.title("🌟 Haber Alpha (Alpha Discovery)")
        st.markdown("""
        Bu VIP modül, teknik analizin ötesine geçerek piyasadaki **Haber-Fiyat Uyuşmazlıkları**nı tespit eder.
        Investing.com Türkiye haber ağını saniyeler içinde tarar, pozitif ayrışma emareleri gösteren şirketlerin son haberlerini **Gemini 3.1 Pro (Flash)** yapay zekasına sokarak şunları denetler:
        - 🧩 **Haberin Niteliği** (Stratejik birleşme mi, olağan bir duyuru mu?)
        - ⏳ **Etki Vadesi** (Kaç gün veya hafta fiyata yön verir?)
        - 💎 **Potansiyel Alpha Skoru** (KAP düşmesine rağmen fiyat henüz hareketlenmemişse fırsat skoru artar)
        """)
        
        st.info("💡 Sistem anlık olarak ulusal borsa haber akışlarına (RSS) canlı bağlanıp binlerce veri setini paralel analiz eder (Çalışması ortalama 30-60 SN sürebilir).")
        
        if st.button("🚀 Alpha Avını Başlat", type="primary"):
            from news_alpha_analyzer import run_alpha_discovery_pipeline
            p_bar = st.progress(0, text="Haber akışları toplanıyor...")
            alpha_res_df = run_alpha_discovery_pipeline(progress_bar=p_bar)
            p_bar.empty()
            
            if not alpha_res_df.empty:
                st.success(f"Taramalar tamamlandı! Keşfedilen potansiyel Alpha hisse sayısı: {len(alpha_res_df)}")
                
                # Checkbox mantığı
                alpha_res_df.insert(0, "Seç", False)
                
                def style_alpha(row):
                    styles = [''] * len(row)
                    for i, col in enumerate(alpha_res_df.columns):
                        val = row[col]
                        if col == 'Önem Skoru':
                            if val >= 80: styles[i] = 'background-color: #2d6a2e; color: white; font-weight: bold'
                            elif val >= 60: styles[i] = 'background-color: #b7950b; color: black; font-weight: bold'
                        elif col == 'AI Tahmini':
                            if str(val).upper() == 'EVET': styles[i] = 'color: #00ff00; font-weight: bold'
                            elif str(val).upper() == 'HAYIR': styles[i] = 'color: #ff4c4c; font-weight: bold'
                    return styles
                
                edited_alpha = st.data_editor(
                    alpha_res_df.style.apply(style_alpha, axis=1),
                    column_config={
                        "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                        "Önem Skoru": st.column_config.ProgressColumn("Alpha Skoru", format="%d", min_value=0, max_value=100)
                    },
                    disabled=[col for col in alpha_res_df.columns if col != "Seç"],
                    hide_index=True,
                    width='stretch',
                    key="alpha_editor"
                )
                
                selected_alphas = edited_alpha[edited_alpha["Seç"] == True]
                if not selected_alphas.empty:
                    st.write(f"✅ {len(selected_alphas)} Alpha listeye alındı.")
                    with st.expander("📥 Seçilenleri Portföye Ekle", expanded=True):
                        adet = st.number_input("Varsayılan Adet", min_value=1.0, value=100.0, key="alpha_adet")
                        if st.button("🌟 Listeyi Toplu Ekle", type="primary", key="alpha_ekle"):
                            for _, row in selected_alphas.iterrows():
                                ticker = row['Sembol']
                                current_px = get_live_price(ticker)
                                pf.alis_yap(current_user, ticker, adet, current_px, not_text="Alpha Discovery üzerinden eklendi.")
                            st.success("Seçilen Alpha adayları Sanal Portföyünüze dinamik korumalarıyla birlikte (SL/TP) eklendi!")
            else:
                st.warning("Şu anki piyasa koşullarında net bir fiyat-haber (Alpha) ayrıcalığı bulunamadı.")
                

    elif mode == "🎯 20 Günlük Trader Disiplini":
        st.title("🎯 20 Günlük Trader Disiplini")
        st.markdown("""
        Bu modül, **matematiksel disiplin** ve **sabit kâr** mantığıyla kasanızı büyütmeyi hedefler.
        Hedef: 20 iş gününün en az 10 gününde **%3 net kâr** yakalamak.
        """)

        # --- Dashboard ---
        col1, col2, col3, col4 = st.columns(4)
        capital = col1.number_input("Başlangıç Sermayesi (TL)", min_value=1000, value=100000, step=1000)
        daily_target_pct = col2.number_input("Günlük Hedef (%)", min_value=0.1, max_value=10.0, value=3.0)
        target_days = col3.number_input("Hedeflenen Başarı Günü", min_value=1, max_value=20, value=10)
        
        fixed_daily_profit = (capital * daily_target_pct / 100)
        final_goal = capital + (fixed_daily_profit * target_days)
        
        stats = tgm.get_trading_stats(current_user)
        current_balance = capital + stats['total_profit']
        progress_pct = min(100.0, (stats['success_days'] / target_days) * 100) if target_days > 0 else 0
        
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Mevcut Kasa", f"{current_balance:,.0f} TL")
        m2.metric("🎯 Final Hedefi", f"{final_goal:,.0f} TL", f"+{final_goal - capital:,.0f} TL")
        m3.metric("✅ Başarılı Gün", f"{stats['success_days']} / {target_days}")
        m4.metric("📈 Win Rate", f"%{stats['win_rate']}")
        
        st.write("**📊 İlerleme Durumu**")
        st.progress(progress_pct / 100, text=f"Hedef Yolculuğu: {progress_pct:.1f}%")
        
        if progress_pct >= 100:
            st.balloons()
            st.success("🎊 TEBRİKLER! 20 günlük disiplin hedefinize ulaştınız. Kasanızı başarıyla büyüttünüz.")

        st.markdown("---")
        
        # --- Volatilite Bazlı Hisse Önerisi ---
        st.subheader("🚀 Hedef Uygunluğu Olan Hisseler")
        st.caption(f"Sadece son 10 günlük ortalama hareketi (ATR) %{daily_target_pct} ve üzeri olan, yani hedefi vurma potansiyeli yüksek hisseler.")
        
        # Kullanıcının son tarama sonuçlarını session_state'de tutalım
        if 'suitable_stocks' not in st.session_state:
            st.session_state.suitable_stocks = []
        if 'discipline_trade_sym' not in st.session_state:
            st.session_state.discipline_trade_sym = ""

        scan_list = BIST30_SYMBOLS
        current_suitable = []
        
        if st.button("🔍 Volatilite Taramasını Başlat"):
            prog = st.progress(0)
            for i, sym in enumerate(scan_list):
                v_df = fetch_data(sym, "1d", "1mo")
                vol_data = tgm.calculate_atr_volatility(v_df, window=10)
                if vol_data['is_suitable']:
                    # Teknik skoru da indicators'dan alalım
                    v_df = calculate_indicators(v_df)
                    sig = generate_signals_and_score(v_df)
                    current_suitable.append({
                        "Seç": False,
                        "Hisse": sym,
                        "Fiyat": v_df['Close'].iloc[-1],
                        "ATR (%)": vol_data['atr_pct'],
                        "Teknik Skor": sig['score'],
                        "Karar": sig['decision']
                    })
                prog.progress((i+1)/len(scan_list))
            st.session_state.suitable_stocks = current_suitable
            st.rerun()
            
        if st.session_state.suitable_stocks:
            suitable_df = pd.DataFrame(st.session_state.suitable_stocks).sort_values(by="Teknik Skor", ascending=False)
            
            edited_df = st.data_editor(
                suitable_df,
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                    "Teknik Skor": st.column_config.ProgressColumn("Güç", format="%d", min_value=0, max_value=100)
                },
                width='stretch',
                hide_index=True,
                key="discipline_editor"
            )
            
            # Seçim değiştiyse trade_sym'i güncelle
            selected_rows = edited_df[edited_df["Seç"] == True]
            if not selected_rows.empty:
                new_sym = selected_rows.iloc[-1]["Hisse"]
                if new_sym != st.session_state.discipline_trade_sym:
                    st.session_state.discipline_trade_sym = new_sym
                    st.rerun()
        else:
            if not st.session_state.suitable_stocks:
                st.info("Hisse bulmak için yukarıdaki taramayı başlatın.")

        st.markdown("---")
        
        # --- Günlük İşlem Kaydı ---
        st.subheader("📝 Günlük İşlem Kaydı")
        c1, c2, c3 = st.columns([1, 1, 1])
        # session_state'den gelen varsayılan değer
        trade_sym = c1.text_input("Bugün İşlem Yapılan Hisse", st.session_state.discipline_trade_sym).upper()
        if trade_sym:
            live_px = get_live_price(trade_sym)
            levels = tgm.get_risk_levels(live_px, target_pct=daily_target_pct)
            c2.info(f"🎯 Hedef: {levels['target']} ₺")
            c3.warning(f"🛑 Stop: {levels['stop']} ₺")
            
            # Canlı Takip & Disiplin Uyarısı
            pct_change = 0
            # Basitleştirilmiş gün içi takip simülasyonu (veya son fiyat üzerinden)
            current_px = get_live_price(trade_sym)
            pct_change = ((current_px - live_px) / live_px) * 100
            
            if pct_change >= daily_target_pct:
                st.markdown(f"""
                <div style="background-color: #064e3b; padding: 20px; border-radius: 10px; border: 2px solid #059669; text-align: center;">
                    <h2 style="color: #34d399; margin: 0;">✅ GÜNLÜK HEDEF TAMAMLANDI!</h2>
                    <p style="color: white; font-size: 1.2rem;">{trade_sym} hissesinde %{pct_change:.2f} kâra ulaşıldı. <b>LÜTFEN EKRANI KAPATIN</b> ve disiplini bozmayın.</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("🏆 Başarılı Günü Kaydet"):
                    tgm.save_daily_result(current_user, trade_sym, True, fixed_daily_profit, daily_target_pct)
                    st.success("Başarı kaydedildi. Yarın görüşmek üzere!")
                    st.rerun()
            elif pct_change <= -1.5:
                st.error(f"🛑 STOP SEVİYESİNE ULAŞILDI (%{pct_change:.2f}). Disiplin gereği pozisyonu kapatmanız önerilir.")
                if st.button("📉 Zararlı Günü Kaydet"):
                    tgm.save_daily_result(current_user, trade_sym, False, - (capital * 0.015), daily_target_pct)
                    st.rerun()

        with st.expander("📖 Geçmiş İşlemler"):
            if stats['history']:
                st.table(stats['history'])
            else:
                st.info("Henüz kayıtlı işlem bulunmuyor.")
    elif mode == "🔒 Profil ve Güvenlik":
        st.title("🔒 Profil ve Güvenlik")
        st.write(f"Mevcut Kullanıcı: **{current_user}**")
        
        st.markdown("---")
        st.subheader("🔑 Şifre Değiştir")
        with st.form("pwd_form"):
            new_p = st.text_input("Yeni Şifre", type="password")
            confirm_p = st.text_input("Yeni Şifre (Tekrar)", type="password")
            save_p = st.form_submit_button("Şifreyi Güncelle")
            if save_p:
                if new_p == confirm_p and len(new_p) >= 4:
                    if auth.update_password(current_user, new_p):
                        st.success("Şifreniz başarıyla güncellendi!")
                    else:
                        st.error("Bir hata oluştu.")
                else:
                    st.error("Şifreler eşleşmiyor veya çok kısa.")
        
        st.markdown("---")
        st.subheader("🗑️ Hesabımı Temizle")
        st.warning("Bu işlem portföyünüzü ve izleme listenizi kalıcı olarak silecektir.")
        if st.checkbox("Tüm verilerimi silmeyi onaylıyorum."):
            if st.button("🚩 Verileri Temizle"):
                pf.portfoy_temizle(current_user)
                st.success("Tüm verileriniz temizlendi.")

if __name__ == "__main__":
    main()
