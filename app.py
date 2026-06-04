import streamlit as st
import pandas as pd
import yfinance as yf
import os

APP_VERSION = "v3.0.2"

# warrant modülleri devre dışı
# from warrant_engine import WarrantEngine as we
# import warrant_data as wd
# import warrant_scraper as ws
import numpy as np
import requests
import time
from datetime import datetime
import pytz
TR_TZ = pytz.timezone("Europe/Istanbul")
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_loader import fetch_data, get_db_stats, clear_db, get_ticker_db_info, get_live_price
from indicators import calculate_indicators, generate_signals_and_score, get_market_regime
from visualizations import create_advanced_chart, create_ml_chart, create_equity_curve_chart, create_signals_chart
from signals_engine import generate_historical_signals, backtest_signals
from screener import (run_screener, BIST30_SYMBOLS, BIST100_SYMBOLS, BIST_ALL_SYMBOLS, 
                      save_scan_results, get_sector_list, filter_by_sector, 
                      get_scan_history, get_persistent_signals,
                      add_to_watchlist, remove_from_watchlist, get_watchlist)

from telegram_utils import send_telegram_report
from advanced_backtest import run_advanced_backtest
from support_resistance import calculate_best_zones
from alerts import check_hybrid_alerts
import portfolio as pf
from takas_engine import get_takas_data
import plotly.express as px
from kap_news import render_kap_news_panel, get_sentiment_summary
from top_picks import (find_top_picks, save_top_picks_history, 
                        get_top_picks_history_dates, get_top_picks_by_date)
import auth
from risk_manager import (
    calculate_atr_stops, calculate_kelly_criterion, calculate_position_size,
    calculate_portfolio_var, calculate_portfolio_correlation,
    calculate_max_drawdown_risk, get_risk_dashboard_data
)
from alert_manager import (
    create_alert, check_alerts, delete_alert, deactivate_alert,
    get_active_alerts, get_alert_history, get_all_alerts,
    ALERT_TYPES, get_alert_type_label, get_alert_type_options,
    get_alert_type_labels, get_default_threshold, get_threshold_label
)
from strategy_comparator import (
    compare_strategies, get_best_strategy, STRATEGY_NAMES, STRATEGY_RUNNERS
)

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
    
    def _get_yf_session():
        """Yahoo Finance için basitleştirilmiş tarayıcı kimliği."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        return session

    @st.cache_data(ttl=60)
    def fetch_market_snapshot():
        # Ana semboller ve alternatif (fallback) sembolleri tanımlayalım
        symbols_map = {
            "BIST 100": ["XU100.IS", "^XU100"], 
            "BIST 30": ["XU030.IS", "^XU030"], 
            "USD/TRY": ["USDTRY=X", "TRY=X"], 
            "EUR/TRY": ["EURTRY=X", "EURTRY=X"],
            "BTC/USD": ["BTC-USD"], 
            "ETH/USD": ["ETH-USD"],
            "Altın Ons": ["GC=F", "GC=F"], 
            "Gümüş Ons": ["SI=F", "SI=F"],
            "Brent Petrol": ["BZ=F", "BZ=F"]
        }
        
        def fetch_single(label, sym_list):
            session = _get_yf_session()
            
            def _try_download(use_session):
                for sym in sym_list:
                    try:
                        current_session = session if use_session else None
                        d = yf.download(sym, period="1mo", interval="1d", progress=False, 
                                        auto_adjust=False, repair=True, group_by="ticker",
                                        session=current_session, threads=False)
                        
                        if d.empty: continue
                        
                        # MultiIndex handle
                        if isinstance(d.columns, pd.MultiIndex):
                            if sym in d.columns.get_level_values(1): d = d.xs(sym, axis=1, level=1)
                            elif sym in d.columns.get_level_values(0): d = d.xs(sym, axis=1, level=0)
                            else: d.columns = d.columns.droplevel(1)
                        
                        ticker_data = d.dropna(subset=['Close'])
                        if not ticker_data.empty:
                            px = float(ticker_data['Close'].iloc[-1])
                            prev_px = float(ticker_data['Close'].iloc[-2]) if len(ticker_data) >= 2 else px
                            return {"val": px, "chg": px - prev_px}
                    except:
                        continue
                return None

            # 1. Deneme: Session ile
            res = _try_download(use_session=True)
            if res: return label, res
            
            # 2. Deneme: Yalın
            time.sleep(0.4) # Bot tespitini zorlaştıran gecikme
            res = _try_download(use_session=False)
            if res: return label, res
            
            return label, {"val": 0, "chg": 0}

        # Paralel İşlemi Başlat (Dirençli Mod: 5 Worker + Jitter)
        res = {label: {"val": 0, "chg": 0} for label in symbols_map}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for label, syms in symbols_map.items():
                futures.append(executor.submit(fetch_single, label, syms))
                time.sleep(0.1) # Burst etkisini azaltmak için mikrosaniye bekleme
                
            for future in as_completed(futures):
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

        .m-lbl {{ color: #888; font-size: 0.62rem; text-transform: uppercase; font-weight: bold; letter-spacing: 0.3px; }}
        .m-val {{ font-weight: 800; font-size: 0.88rem; margin-top: 1px; }}
        .val-up {{ color: #26de81; }}
        .val-down {{ color: #ff4757; }}

        /* Market Grid (Integrated) */
        .market-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 25px;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .m-card-grid {{
            text-align: center;
            padding: 8px 4px;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}
        .m-card-grid:hover {{ background: rgba(255,255,255,0.03); transform: translateY(-2px); }}
        .grid-up {{ border-bottom: 2px solid #26de81; }}
        .grid-down {{ border-bottom: 2px solid #ff4757; }}

        /* Live Indicator */
        .live-dot {{
            height: 8px;
            width: 8px;
            background-color: #26de81;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
            box-shadow: 0 0 8px #26de81;
            animation: pulse-dot 2s infinite;
        }}
        @keyframes pulse-dot {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(38, 222, 129, 0.7); }}
            70% {{ transform: scale(1); box-shadow: 0 0 0 10px rgba(38, 222, 129, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(38, 222, 129, 0); }}
        }}

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
                <div style="margin-top:10px; font-weight:bold; color:var(--emerald); font-size:0.8rem;">{v} PRO</div>
                <div style="margin-top:15px; font-size:0.7rem; color:#888;">
                    <span class="live-dot"></span> LIVE MARKET DATA
                </div>
            </div>
        """.format(v=APP_VERSION), unsafe_allow_html=True)

        with st.form("auth_form_final"):
            u_input = st.text_input("Kullanıcı Adı", placeholder="user")
            p_input = st.text_input("Giriş Şifresi", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sisteme Giriş Yap", type="primary", use_container_width=True)
            
            if submitted:
                if auth.verify_login(u_input, p_input):
                    st.session_state.logged_in = True
                    st.session_state.username = u_input
                    st.rerun()
                else:
                    st.error("🔑 Hatalı Giriş Bilgileri")

        # Market Grid İnşası
        grid_html = ""
        for lbl, data in market_data.items():
            val = data.get("val", 0)
            chg = data.get("chg", 0)
            fmt = f"{val:,.0f}" if val > 1000 else f"{val:.2f}"
            if val == 0: fmt = "N/A"
            
            arrow = "▲" if chg >= 0 else "▼"
            c_class = "grid-up" if chg >= 0 else "grid-down"
            v_class = "val-up" if chg >= 0 else "val-down"
            
            grid_html += f'<div class="m-card-grid {c_class}"><div class="m-lbl">{lbl}</div><div class="m-val {v_class}">{arrow} {fmt}</div></div>'
        
        st.markdown(f'<div class="market-grid">{grid_html}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


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
    
    # Versiyon Bilgisi
    st.sidebar.markdown("---")
    st.sidebar.caption(f"🏷️ **Versiyon: {APP_VERSION}**")

    # Navigasyon
    mode = st.sidebar.radio("📁 Terminal Modülleri", [
        "📊 Hisse Profili ve Derinlik Analizi",
        "🚦 Al-Sat Sinyali",
        "🔍 Piyasa Tarama Terminali (Screener)",
        "💼 Gelişmiş Backtest",
        "🧪 Strateji Karşılaştırma Motoru",
        "📈 Sanal Portföy",
        "⚠️ Risk Yönetim Merkezi",
        "🔔 Alarm Merkezi",
        "📰 KAP ve Haberler",
        "🏆 Stratejik Seçki (Top Picks)",
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

        # Ephemeral Storage Uyarısı (Streamlit Cloud için)
        if os.name == 'posix': # Linux/Unix ortamı
            st.warning("⚠️ **Bulut Ortamı Saptandı:** SQLite veritabanı platform tarafından her deploy sonrasında sıfırlanabilir. Kalıcılık için harici bir DB (Supabase vb.) önerilir.")
        
        st.info(f"🕒 **Sistem Saati (TR):** {datetime.now(TR_TZ).strftime('%H:%M:%S')}")

    

    if mode == "📊 Hisse Profili ve Derinlik Analizi":
        st.title("📊 Hisse Profili ve Derinlik Analizi")
        st.caption("Bu modül, hisse senedinin anlık fiyatını, temel verilerini ve hacim analizlerini incelerken aynı zamanda arka planda çalışan **100 adet teknik indikatörden** elde edilen \"Ana Sinyal\" durumunu detaylı bir şekilde raporlar.")
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
            
            df = calculate_indicators(df, ticker=sym)
            
            # --- Hibrit Duygu Analizi Çek ---
            with st.spinner("🤖 Haber Akışı AI ile analiz ediliyor..."):
                sent_score, news_list = get_sentiment_summary(sym)
                
            res = generate_signals_and_score(df, ticker=sym, market_regime=market_regime, sentiment_score=sent_score)
            live_px = df['Close'].iloc[-1]
            sr_data = calculate_best_zones(df)
            
            # Hisse adı ve günlük değişimi çek
            stock_name = sym.upper()
            daily_change = 0.0
            daily_change_pct = 0.0
            try:
                t = yf.Ticker(sym + ".IS")
                info = t.info
                stock_name = info.get('shortName', info.get('longName', sym.upper()))
                if len(df) >= 2:
                    prev_close = float(df['Close'].iloc[-2])
                    daily_change = live_px - prev_close
                    daily_change_pct = (daily_change / prev_close) * 100 if prev_close > 0 else 0
            except Exception:
                if len(df) >= 2:
                    prev_close = float(df['Close'].iloc[-2])
                    daily_change = live_px - prev_close
                    daily_change_pct = (daily_change / prev_close) * 100 if prev_close > 0 else 0

            chg_color = "#26de81" if daily_change >= 0 else "#ff4757"
            chg_arrow = "▲" if daily_change >= 0 else "▼"
            chg_sign = "+" if daily_change >= 0 else ""
            
            c1, c2 = st.columns([1.2, 2])
            with c1:
                # Premium Hisse Başlık Kartı
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #0f172a, #1e293b); padding: 20px; border-radius: 12px; border: 1px solid rgba(74,222,128,0.2); margin-bottom: 15px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="background: rgba(74,222,128,0.15); padding: 8px 14px; border-radius: 8px;">
                                <span style="font-size: 1.6rem; font-weight: 900; color: #4ade80;">{sym.upper()}</span>
                            </div>
                            <div>
                                <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600;">{stock_name}</div>
                            </div>
                        </div>
                        <div style="margin-top: 12px; display: flex; align-items: baseline; gap: 10px;">
                            <span style="font-size: 2rem; font-weight: 900; color: white;">{live_px:,.2f} ₺</span>
                            <span style="font-size: 1rem; font-weight: 700; color: {chg_color};">{chg_arrow} {chg_sign}{daily_change:,.2f} ({chg_sign}{daily_change_pct:.2f}%)</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # --- PREMIUM STYLED METRICS ---
                decision_label = res.get('core_decision', res.get('decision', 'N/A'))
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

                # Skorlar ve Takas (Gelişmiş Metrik Barı)
                col_s1, col_s2, col_s3 = st.columns(3)
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
                with col_s3:
                    takas_info = get_takas_data(sym)
                    fr = takas_info.get('foreign_ratio', 0.0)
                    dc = takas_info.get('daily_change', 0.0)
                    t_color = "#26de81" if dc > 0 else "#ff4757" if dc < 0 else "gray"
                    t_sign = "+" if dc > 0 else ""
                    st.markdown(f"""
                        <div style="text-align: center; border: 1px solid #3e3e3e; padding: 10px; border-radius: 10px; background-color: #1e1e1e;">
                            <div style="color: #38bdf8; font-size: 1.5rem; font-weight: bold;">%{fr:.2f}</div>
                            <div style="color: {t_color}; font-size: 0.75rem; font-weight: bold;">{t_sign}{dc:.2f}% (Değişim)</div>
                            <div style="color: gray; font-size: 0.7rem;">Yabancı Takas Payı</div>
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
                rc1, rc2, rc3, rc4 = st.columns(4)
                rc1.metric("Stop Loss", f"{risk_data.get('SL', 0):.2f}")
                rc2.metric("İzleyen Stop (TS)", f"{risk_data.get('TrailingStop', 0):.2f}")
                rc3.metric("Hedef 1 (TP1)", f"{risk_data.get('TP1', 0):.2f}")
                rc4.metric("Hedef 2 (TP2)", f"{risk_data.get('TP2', 0):.2f}")

                # --- TELEGRAM RAPORLAMA ---
                st.write("---")
                if st.button("📤 Analizi Telegram'a Gönder", use_container_width=True):
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
                st.plotly_chart(fig, use_container_width=True)

    elif mode == "🚦 Al-Sat Sinyali":
        st.title("🚦 Al-Sat Sinyali Terminali")
        st.caption("Terminal, **100 adet teknik indikatör** ve süre kombinasyonunu geriye dönük test eder, bu hisse senedinde en yüksek tarihsel başarıya sahip 15 indikatörü seçer ve ağırlıklı oylamayla dinamik AL/SAT sinyalleri üretir.")
        sym = st.sidebar.text_input("Hisse Kodu (Örn: EREGL)", "THYAO")
        
        # Sinyal Hassasiyet Ayarı
        sensitivity = st.sidebar.selectbox("🎯 Algoritma Hassasiyeti", ["Muhafazakar", "Dengeli", "Agresif"], index=1)
        
        if sym:
            with st.spinner("Veriler işleniyor ve indikatörler hesaplanıyor..."):
                df = fetch_data(sym, "1d", "1y")
            if df.empty:
                st.error("Veri bulunamadı.")
            else:
                df, top_indicators, stats = generate_historical_signals(df, sensitivity)
                
                # Üst Kısım: Strateji İstatistikleri
                st.markdown(f"### 📊 {sym.upper()} Çoklu İndikatör Oylama Başarı Analizi")

                
                # --- ANLIK HAMLE VE KARAR TERMİNALİ ---
                # Son verileri al
                last_row = df.iloc[-1]
                close_px = float(last_row['Close'])

                # Son sinyalleri sorgula
                buy_signals_idx = df[df['Buy_Signal'].notna()].index
                sell_signals_idx = df[df['Sell_Signal'].notna()].index

                last_buy_date = buy_signals_idx[-1] if len(buy_signals_idx) > 0 else None
                last_sell_date = sell_signals_idx[-1] if len(sell_signals_idx) > 0 else None

                # -- SSOT (Single Source of Truth) Karar Motoru Entegrasyonu --
                xu100_df = fetch_data("XU100", "1d", "1y")
                market_regime = get_market_regime(xu100_df)
                try:
                    sent_score, _ = get_sentiment_summary(sym)
                except:
                    sent_score = 0.0
                ssot_res = generate_signals_and_score(df, ticker=sym, market_regime=market_regime, sentiment_score=sent_score)
                decision_label = ssot_res.get('core_decision', 'NÖTR')
                
                if "Al" in decision_label:
                    active_signal = "AL (LONG POZİSYONDA)"
                    active_signal_color = "#26de81" # Neon Yeşil
                    active_action = f"{decision_label.upper()} 🚀"
                    active_action_details = f"SSOT 100-İndikatör motoru {sym.upper()} için güncel olarak '{decision_label}' kararı vermektedir. Diğer modüllerle %100 uyumludur."
                elif "Sat" in decision_label:
                    active_signal = "SAT (SHORT POZİSYONDA)"
                    active_signal_color = "#ff4757" # Kırmızı
                    active_action = f"{decision_label.upper()} 🛑"
                    active_action_details = f"SSOT 100-İndikatör motoru {sym.upper()} için güncel olarak '{decision_label}' kararı vermektedir. Diğer modüllerle %100 uyumludur."
                else:
                    active_signal = "NÖTR"
                    active_signal_color = "#94a3b8" # Gri
                    active_action = "İzleme / Bekle ⚖️"
                    active_action_details = "SSOT 100-İndikatör motoru yatay trend veya nötr piyasa tespit etti. Yeni bir kırılım beklenmeli."

                # Ortalamalar Analizi
                sma_20 = float(last_row['SMA_20']) if 'SMA_20' in last_row and pd.notna(last_row['SMA_20']) else np.nan
                sma_50 = float(last_row['SMA_50']) if 'SMA_50' in last_row and pd.notna(last_row['SMA_50']) else np.nan
                sma_52 = float(last_row['SMA_52']) if 'SMA_52' in last_row and pd.notna(last_row['SMA_52']) else np.nan

                # Ortalama durum metinleri
                sma_20_status = "Üzerinde 📈" if pd.notna(sma_20) and close_px > sma_20 else ("Altında 📉" if pd.notna(sma_20) else "Hesaplanamadı ⚠️")
                sma_20_color = "#26de81" if pd.notna(sma_20) and close_px > sma_20 else "#ff4757"

                sma_50_status = "Üzerinde 📈" if pd.notna(sma_50) and close_px > sma_50 else ("Altında 📉" if pd.notna(sma_50) else "Hesaplanamadı ⚠️")
                sma_50_color = "#26de81" if pd.notna(sma_50) and close_px > sma_50 else "#ff4757"

                sma_52_status = "Üzerinde 📈" if pd.notna(sma_52) and close_px > sma_52 else ("Altında 📉" if pd.notna(sma_52) else "Hesaplanamadı ⚠️")
                sma_52_color = "#26de81" if pd.notna(sma_52) and close_px > sma_52 else "#ff4757"

                # Dashboard Kartları
                st.markdown("### 🎯 Anlık Hamle ve Karar Terminali")
                rec_c1, rec_c2 = st.columns([1.2, 1])
                
                with rec_c1:
                    st.markdown(f"""
                        <div style="background-color: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; height: 100%;">
                            <h5 style="color: #94a3b8; margin-top: 0; margin-bottom: 8px;">🎯 Canlı Hamle Önerisi</h5>
                            <div style="font-size: 1.4rem; color: {active_signal_color}; font-weight: bold; margin-bottom: 10px;">
                                {active_action}
                            </div>
                            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.4; margin-bottom: 8px;">
                                {active_action_details}
                            </p>
                            <div style="margin-top: 15px; font-size: 0.8rem; color: #94a3b8;">
                                <b>Aktif Pozisyon Durumu:</b> <span style="color: {active_signal_color}; font-weight: bold;">{active_signal}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with rec_c2:
                    st.markdown(f"""
                        <div style="background-color: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; height: 100%;">
                            <h5 style="color: #94a3b8; margin-top: 0; margin-bottom: 8px;">📈 Hareketli Ortalama Trend Analizi</h5>
                            <table style="width: 100%; font-size: 0.85rem; border-collapse: collapse;">
                                <tr style="border-bottom: 1px solid #334155; color: #94a3b8;">
                                    <th style="text-align: left; padding: 6px 0;">Ortalama</th>
                                    <th style="text-align: right; padding: 6px 0;">Ortalama Değeri</th>
                                    <th style="text-align: right; padding: 6px 0;">Fiyat Konumu</th>
                                </tr>
                                <tr style="border-bottom: 1px solid #334155;">
                                    <td style="padding: 8px 0; font-weight: bold; color: #cbd5e1;">20 Günlük Kısa Vade (SMA)</td>
                                    <td style="text-align: right; padding: 8px 0; color: #cbd5e1;">{sma_20:.2f} ₺</td>
                                    <td style="text-align: right; padding: 8px 0; color: {sma_20_color}; font-weight: bold;">{sma_20_status}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #334155;">
                                    <td style="padding: 8px 0; font-weight: bold; color: #cbd5e1;">50 Günlük Orta Vade (SMA)</td>
                                    <td style="text-align: right; padding: 8px 0; color: #cbd5e1;">{sma_50:.2f} ₺</td>
                                    <td style="text-align: right; padding: 8px 0; color: {sma_50_color}; font-weight: bold;">{sma_50_status}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; font-weight: bold; color: #cbd5e1;">52 Günlük Trend Ortalaması (SMA)</td>
                                    <td style="text-align: right; padding: 8px 0; color: #cbd5e1;">{sma_52:.2f} ₺</td>
                                    <td style="text-align: right; padding: 8px 0; color: {sma_52_color}; font-weight: bold;">{sma_52_status}</td>
                                </tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                st.write("")
                st.write("---")
                
                # --- SSOT (Single Source of Truth) DETAYLI ANALİZ ---
                st.write("---")
                st.markdown("### 🚦 Canlı Çoklu İndikatör Oylama Dağılımı")
                
                total = ssot_res.get('total_votes', 1)
                if total == 0: total = 1
                buy_strength = (ssot_res.get('buy_votes', 0) / total) * 100
                sell_strength = (ssot_res.get('sell_votes', 0) / total) * 100
                neut_strength = max(0.0, 100.0 - buy_strength - sell_strength)
                
                # Canlı oylama barı
                st.markdown(f"""
                    <div style="margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 0.85rem; margin-bottom: 5px;">
                            <span style="color: #26de81;">🟢 AL Yönü (%{buy_strength:.0f})</span>
                            <span style="color: #94a3b8;">⚖️ NÖTR Yönü (%{neut_strength:.0f})</span>
                            <span style="color: #ff4757;">🔴 SAT Yönü (%{sell_strength:.0f})</span>
                        </div>
                        <div style="display: flex; height: 24px; border-radius: 6px; overflow: hidden; border: 1px solid #334155;">
                            <div style="width: {buy_strength}%; background-color: #26de81; transition: width 0.5s;"></div>
                            <div style="width: {neut_strength}%; background-color: #475569; transition: width 0.5s;"></div>
                            <div style="width: {sell_strength}%; background-color: #ff4757; transition: width 0.5s;"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### 📝 Yapay Zeka Karar Özeti (Neden AL veya SAT?)")
                summary_text = ssot_res.get('summary', 'Analiz detayı bulunamadı.')
                if summary_text:
                    st.info(summary_text)
                    
                st.write("---")
                st.write("---")
                st.markdown("### 🔍 SSOT İndikatör Kanıtları (Algoritma Arka Planı)")
                st.caption("Yapay zekanın karar verirken baz aldığı 100+ indikatör kümesinden (Ensemble) öne çıkanların güncel durumları.")
                
                core_votes = ssot_res.get('core_votes_list', [])
                if core_votes:
                    proof_df = pd.DataFrame(core_votes)
                    st.dataframe(proof_df, height=300, use_container_width=True, hide_index=True)
                    
                    al_count = sum(1 for v in core_votes if "AL" in v.get("Durum", ""))
                    sat_count = sum(1 for v in core_votes if "SAT" in v.get("Durum", ""))
                    notr_count = sum(1 for v in core_votes if "NÖTR" in v.get("Durum", ""))
                    
                    st.markdown(f"**Toplam listelenen Kural/İndikatör sayısı:** {len(proof_df)}")
                    st.caption(f"🟢 **AL Diyenler:** {al_count} adet | 🔴 **SAT Diyenler:** {sat_count} adet | ⚖️ **NÖTR Kalanlar:** {notr_count} adet")
                else:
                    st.info("İndikatör detayları gösterilemiyor.")

                st.write("---")
                # SSOT sonucuna göre grafiğin SON MUMUNU (Anlık Karar) güncelle
                import numpy as np
                if df is not None and not df.empty:
                    # Eski 15'li indikatörden kalan son gün oylarını temizle
                    if 'Buy_Signal' in df.columns:
                        df.loc[df.index[-1], 'Buy_Signal'] = np.nan
                    if 'Sell_Signal' in df.columns:
                        df.loc[df.index[-1], 'Sell_Signal'] = np.nan
                    
                    ssot_decision_label = ssot_res.get('core_decision', 'Nötr').upper()
                    last_low = df['Low'].iloc[-1]
                    last_high = df['High'].iloc[-1]
                    
                    if "AL" in ssot_decision_label:
                        if 'Buy_Signal' not in df.columns: df['Buy_Signal'] = np.nan
                        if 'Signal_Reason' not in df.columns: df['Signal_Reason'] = ""
                        df.loc[df.index[-1], 'Buy_Signal'] = last_low * 0.98
                        df.loc[df.index[-1], 'Signal_Reason'] = "SSOT Kararı: " + ssot_decision_label
                    elif "SAT" in ssot_decision_label:
                        if 'Sell_Signal' not in df.columns: df['Sell_Signal'] = np.nan
                        if 'Signal_Reason' not in df.columns: df['Signal_Reason'] = ""
                        df.loc[df.index[-1], 'Sell_Signal'] = last_high * 1.02
                        df.loc[df.index[-1], 'Signal_Reason'] = "SSOT Kararı: " + ssot_decision_label

                # Plotly Grafiği Çizimi (Ana Grafik)
                fig_sig = create_signals_chart(df, sym.upper())
                st.plotly_chart(fig_sig, use_container_width=True)

    elif mode == "🔍 Piyasa Tarama Terminali (Screener)":
        st.title("🔍 Piyasa Tarama Terminali (Screener)")
        st.caption("BIST üzerindeki yüzlerce hisseyi saniyeler içinde **100 adet teknik indikatör**, hacim kırılımları ve temel finansal verilere göre tarayarak piyasadaki en güçlü alım/satım fırsatlarını puanlar ve listeler.")
        
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
        filter_option = st.sidebar.selectbox("🚀 Hazır Stratejik Filtreler", [
            "Tümünü Göster", 
            "💎 Sadece Güçlü Al (V6 > 75)", 
            "🔥 Squeeze (Sıkışma) Olanlar", 
            "🚀 Squeeze Ateşlenenler",
            "🛡️ SMC / Stop Avı Tespiti",
            "💹 Hacim (OBV) Diverjansı",
            "💪 Endeksten Güçlüler (Alpha > 2%)",
            "📊 R/R Oranı > 2.5 Olanlar",
            "Çift AL (1D+1H) Teyitliler",
            "Hacim Patlaması Olanlar"
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
        
        # Sıralama Kriteri Seçimi
        sort_criterion = st.sidebar.selectbox(
            "📊 Tablo Sıralama Kriteri",
            [
                "Ensemble Güven Skoru (Önerilen)",
                "V6 Hibrit Skor",
                "Güven Skoru (PGS)",
                "Desteğe En Yakın Hisseler"
            ],
            index=0
        )
        
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
            
            # Dinamik Sıralama Uygula
            if sort_criterion == "Ensemble Güven Skoru (Önerilen)":
                if "Ensemble Güven Skoru" in screener_df.columns:
                    screener_df = screener_df.sort_values(by="Ensemble Güven Skoru", ascending=False).reset_index(drop=True)
            elif sort_criterion == "V6 Hibrit Skor":
                screener_df = screener_df.sort_values(by="V6 Hibrit Skor", ascending=False).reset_index(drop=True)
            elif sort_criterion == "Güven Skoru (PGS)":
                screener_df = screener_df.sort_values(by="Güven Skoru (PGS)", ascending=False).reset_index(drop=True)
            elif sort_criterion == "Desteğe En Yakın Hisseler":
                def get_dist_num(val):
                    if val == "Destekte": return -0.1
                    try: return float(str(val).replace('%','').strip())
                    except: return 999.0
                if "Desteğe Uzaklık" in screener_df.columns:
                    screener_df['temp_sort'] = screener_df['Desteğe Uzaklık'].apply(get_dist_num)
                    screener_df = screener_df.sort_values(by="temp_sort", ascending=True).drop(columns=['temp_sort']).reset_index(drop=True)
            
            # Filtreleme uygula
            if filter_option == "💎 Sadece Güçlü Al (V6 > 75)":
                screener_df = screener_df[screener_df['V6 Hibrit Skor'] >= 75]
            elif filter_option == "🔥 Squeeze (Sıkışma) Olanlar":
                screener_df = screener_df[screener_df['Sıkışma Durumu'] == 'Sıkışma 🔥']
            elif filter_option == "🚀 Squeeze Ateşlenenler":
                screener_df = screener_df[screener_df['Sıkışma Durumu'] == 'Ateşlendi 🚀']
            elif filter_option == "🛡️ SMC / Stop Avı Tespiti":
                screener_df = screener_df[screener_df['SMC / Stop Avı'] != '-']
            elif filter_option == "💹 Hacim (OBV) Diverjansı":
                screener_df = screener_df[screener_df['Hacim Diverjans'] != '-']
            elif filter_option == "💪 Endeksten Güçlüler (Alpha > 2%)":
                def parse_alpha(x):
                    try: return float(str(x).replace('%','')) if x != '-' else -99
                    except: return -99
                screener_df = screener_df[screener_df['Göreceli Güç (Alpha)'].apply(parse_alpha) >= 2.0]
            elif filter_option == "📊 R/R Oranı > 2.5 Olanlar":
                screener_df = screener_df[screener_df['Risk/Ödül (R/R)'] >= 2.5]
            elif filter_option == "Çift AL (1D+1H) Teyitliler":
                screener_df = screener_df[screener_df['1D+1H Uyum'].str.contains('Çift AL', na=False)]
            
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
                st.plotly_chart(fig_matrix, use_container_width=True)
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
                        elif col == 'Ensemble Güven Skoru':
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
                        elif col == 'SMC / Stop Avı':
                            if val != '-': styles[i] = 'background-color: #512e5f; color: #d4e6f1; font-weight: bold'
                        elif col == 'Sıkışma Durumu':
                            if '🔥' in str(val): styles[i] = 'background-color: #7b241c; color: white; font-weight: bold'
                            elif '🚀' in str(val): styles[i] = 'background-color: #145a32; color: white; font-weight: bold'
                        elif col == 'Göreceli Güç (Alpha)':
                            if '+' in str(val): styles[i] = 'color: #00ff00; font-weight: bold'
                        elif col == 'Risk/Ödül (R/R)':
                            if float(val) >= 2.5: styles[i] = 'color: #00ff00; font-weight: bold'
                            elif float(val) < 1.0: styles[i] = 'color: #ff4c4c'
                        elif col == '1D+1H Uyum':
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
                    use_container_width=True,
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
                st.download_button("📥 Sonuçları CSV Olarak İndir", csv_data, "tarama_sonuclari.csv", "text/csv", use_container_width=True)
                
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
                            st.plotly_chart(fig_q, use_container_width=True)
                            
                            # RSI paneli
                            if 'RSI_14' in qdf.columns:
                                fig_rsi = go.Figure()
                                fig_rsi.add_trace(go.Scatter(x=qdf.index, y=qdf['RSI_14'], line=dict(color='magenta'), name='RSI 14'))
                                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Aşırı Alım")
                                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Aşırı Satım")
                                fig_rsi.update_layout(template='plotly_dark', height=200, title="RSI (14)")
                                st.plotly_chart(fig_rsi, use_container_width=True)
                
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
                st.dataframe(persistent_df.style.format(precision=2), use_container_width=True)
            else:
                st.info("Henüz birden fazla gün tarama geçmişi oluşmamış. Her gün tarama yaparak tutarlı sinyalleri burada göreceksiniz.")
        
        # ---- WATCHLIST (Özellik 8) ----
        with st.expander("🔔 İzleme Listem (Watchlist)"):
            wl_df = get_watchlist(current_user)
            if not wl_df.empty:
                st.dataframe(wl_df.style.format(precision=2), use_container_width=True)
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


    elif mode == "💼 Gelişmiş Backtest":
        st.title("💼 Kurumsal Portföy Backtest Simülatörü")
        st.caption("Gelişmiş backtest motoru, **100 farklı teknik indikatörden** oluşan stratejinin geçmiş verilere uygulandığında nasıl bir getiri eğrisi çizeceğini komisyon, kayma (slippage) ve risk parametreleriyle simüle eder.")
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
                st.markdown("### 📊 Backtest Sonuçları (Alfa ve Performans)")
                c1, c2, c3 = st.columns(3)
                c1.metric("Nihai Portföy Değeri", f"₺{res['final_equity']:,.2f}", f"{res['total_return_pct']:.2f}% (Brüt Getiri)")
                c2.metric("Maksimum Kayıp (Drawdown)", f"{res['max_drawdown_pct']:.2f}%", delta_color="inverse")
                c3.metric("Toplam İşlem Sayısı", f"{res['number_of_trades']}")

                st.markdown("#### 🥇 Piyasa Kıyaslaması (Alfa Üretimi)")
                ac1, ac2, ac3 = st.columns(3)
                ac1.metric("Risksiz Getiri (Mevduat)", f"{res.get('risk_free_return_pct', 0):.2f}%")
                ac2.metric("Buy&Hold (Al & Tut) Getirisi", f"{res.get('buy_and_hold_return_pct', 0):.2f}%")
                
                alpha_rf = res.get('alpha_rf', 0)
                ac3.metric("Reel Alfa (Mevduat Üstü)", f"{alpha_rf:.2f}%", delta=f"{alpha_rf:.2f}%", delta_color="normal" if alpha_rf >= 0 else "inverse")
                
                st.plotly_chart(create_equity_curve_chart(res['equity_curve'], sym.upper()), use_container_width=True)
                
                with st.expander("Detaylı İşlem Dökümü (Trades)"):
                    if res['trades']:
                        st.table(pd.DataFrame(res['trades']).style.format(precision=2))
                    else:
                        st.write("Belirtilen süre zarfında AL/SAT sinyali üretilmedi.")

    elif mode == "📈 Sanal Portföy":
        st.title("📈 Sanal Portföy Yönetimi")
        st.caption("Sanal portföyünüze eklediğiniz hisselerin kar/zarar durumunu takip edebilir, aynı zamanda **100 indikatörlü ana sinyal motorunun** portföyünüzdeki hisseler için güncel tavsiyelerini izleyebilirsiniz.")
        st.markdown("Beğendiğiniz hisseleri sanal olarak alıp, zaman içindeki başarınızı takip edebilirsiniz.")

        def save_portfolio_changes():
            editor_state = st.session_state.get("portfolio_editor", {})
            changes = editor_state.get("edited_rows", {})
            mapping = st.session_state.get("portfolio_mapping", [])
            
            if changes and mapping:
                for idx_str, row_changes in changes.items():
                    idx = int(idx_str)
                    if idx < len(mapping):
                        trade_id, old_adet, old_fiyat = mapping[idx]
                        new_adet = row_changes.get("Adet", old_adet)
                        new_fiyat = row_changes.get("Maliyet (₺)", old_fiyat)
                        pf.pozisyon_guncelle(trade_id, new_adet, new_fiyat)
                st.session_state['portfolio_saved_msg'] = True
                st.session_state['force_portfolio_refresh'] = True

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
            if st.button("🔄 Canlı Fiyatları Yenile", use_container_width=True):
                st.session_state['force_portfolio_refresh'] = True
                st.rerun()

        acik_df = pf.acik_pozisyonlar(current_user)
        
        if not acik_df.empty:
            p_data = []
            
            if 'portfoy_canli_fiyat' not in st.session_state or st.session_state.get('force_portfolio_refresh'):
                st.session_state['portfoy_canli_fiyat'] = {}
                st.session_state['force_portfolio_refresh'] = False

            fiyatlar_guncellendi = False
            for idx, row in acik_df.iterrows():
                if row['ticker'] not in st.session_state['portfoy_canli_fiyat']:
                    fiyatlar_guncellendi = True
                    break
                    
            if fiyatlar_guncellendi:
                with st.spinner("Anlık fiyatlar piyasadan çekiliyor..."):
                    for idx, row in acik_df.iterrows():
                        ticker = row['ticker']
                        if ticker not in st.session_state['portfoy_canli_fiyat']:
                            curr_price = get_live_price(ticker)
                            if curr_price == 0.0:
                                df_curr = fetch_data(ticker, "1d", "5d")
                                curr_price = df_curr['Close'].iloc[-1] if not df_curr.empty else 0
                            st.session_state['portfoy_canli_fiyat'][ticker] = curr_price

            for idx, row in acik_df.iterrows():
                ticker = row['ticker']
                curr_price = st.session_state['portfoy_canli_fiyat'].get(ticker, 0.0)
                
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
            st.session_state['portfolio_mapping'] = [(r['ID'], r['Adet'], r['Maliyet (₺)']) for r in p_data]

            
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

            # DÜZENLENEBİLİR TABLO ENTEGRASYONU
            edited_df = st.data_editor(
                styled_p_df, 
                column_config={
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "Hisse": st.column_config.TextColumn("Hisse", disabled=True),
                    "Güncel (₺)": st.column_config.NumberColumn("Güncel (₺)", disabled=True),
                    "Stop-Loss": st.column_config.TextColumn("Stop-Loss", disabled=True),
                    "Take-Profit": st.column_config.TextColumn("Take-Profit", disabled=True),
                    "Risk (VaR) ₺": st.column_config.TextColumn("Risk (VaR) ₺", disabled=True),
                    "Kâr/Zarar (₺)": st.column_config.NumberColumn("Kâr/Zarar (₺)", disabled=True),
                    "Değişim (%)": st.column_config.NumberColumn("Değişim (%)", disabled=True),
                    "Tarih": st.column_config.TextColumn("Tarih", disabled=True),
                    "Adet": st.column_config.NumberColumn("Adet", min_value=0.1, required=True),
                    "Maliyet (₺)": st.column_config.NumberColumn("Maliyet (₺)", min_value=0.01, required=True)
                },
                hide_index=True,
                use_container_width=True,
                key="portfolio_editor"
            )
            
            # Değişiklikleri Kontrol Et ve Buton Göster
            if st.session_state.portfolio_editor.get("edited_rows"):
                st.button("💾 Değişiklikleri Veritabanına Kaydet", type="primary", use_container_width=True, on_click=save_portfolio_changes)

            if st.session_state.get('portfolio_saved_msg'):
                st.success("✅ Portföy başarıyla güncellendi!")
                st.session_state['portfolio_saved_msg'] = False

            # DİNAMİK HESAPLAMA: edited_df üzerinden anlık metrikleri hesapla
            toplam_maliyet = (edited_df['Adet'] * edited_df['Maliyet (₺)']).sum()
            toplam_guncel = (edited_df['Adet'] * edited_df['Güncel (₺)']).sum()
            toplam_kz = toplam_guncel - toplam_maliyet
            toplam_yuzde = (toplam_kz / toplam_maliyet) * 100 if toplam_maliyet > 0 else 0
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Toplam Yatırım", f"₺{toplam_maliyet:,.2f}")
            mc2.metric("Portföy Değeri", f"₺{toplam_guncel:,.2f}")
            mc3.metric("Net Kâr/Zarar", f"₺{toplam_kz:,.2f}", f"{toplam_yuzde:.2f}%")

            # Görsel Grafikler İçin Türetilmiş Kolonları Güncelle
            edited_df['Kâr/Zarar (₺)'] = (edited_df['Adet'] * edited_df['Güncel (₺)']) - (edited_df['Adet'] * edited_df['Maliyet (₺)'])
            edited_df['Değişim (%)'] = (edited_df['Kâr/Zarar (₺)'] / (edited_df['Adet'] * edited_df['Maliyet (₺)'])) * 100
            
            st.markdown("---")
            gc1, gc2 = st.columns(2)
            
            with gc1:
                st.subheader("🍕 Portföy Dağılımı")
                fig_pie = px.pie(edited_df, values='Adet', names='Hisse', title='Hisse Dağılımı (Adet Bazlı)', hole=0.4, template='plotly_dark')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with gc2:
                st.subheader("📊 Hisse Bazlı Kar/Zarar")
                p_df_sorted = edited_df.sort_values('Kâr/Zarar (₺)', ascending=False)
                fig_bar = px.bar(p_df_sorted, x='Hisse', y='Kâr/Zarar (₺)', color='Değişim (%)',
                                 title='Hisse Bazlı Kazanç Durumu', template='plotly_dark',
                                 color_continuous_scale=['red', 'yellow', 'green'],
                                 color_continuous_midpoint=0)
                st.plotly_chart(fig_bar, use_container_width=True)

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
            st.dataframe(kapali_df.style.format(precision=2), use_container_width=True)
            
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
        st.caption("Bu modül, **100 adet teknik indikatör skorunu**, temel finansal verileri ve yabancı takas oranlarını harmanlayarak, borsadaki en yüksek potansiyelli 15 hisseyi özel bir algoritma ile bulur.")
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
                    "Göreceli Güç": r.get('alpha_text', '-'),
                    "R/R Rasyosu": r.get('rr_ratio', 0),
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
                    elif col == 'R/R Rasyosu':
                        if isinstance(val, (int, float)) and val >= 3.0: styles[i] = 'color: #00ff00; font-weight: bold'
                        elif isinstance(val, (int, float)) and val < 2.0: styles[i] = 'color: #ff4c4c; font-weight: bold'
                    elif col == 'Göreceli Güç':
                        if '+' in str(val): styles[i] = 'color: #00ff00; font-weight: bold'
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
                use_container_width=True,
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
            if st.button("📤 Haftalık Listeyi Telegram'a Gönder", use_container_width=True):
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
                        "Bileşen": ["📈 Momentum", "🌊 Hacim", "⏰ Çoklu TF", "🕯️ Formasyon", "🛡️ Destek", "📰 Haber", "🔥 Dipten Dönüş", "🏦 Yabancı Takas"],
                        "Bonus Puan": [
                            f"+{pick['momentum_bonus']}",
                            f"+{pick['volume_bonus']}",
                            f"+{pick['tf_bonus']}",
                            f"+{pick['pattern_bonus']}",
                            f"+{pick['support_bonus']}",
                            f"+{pick['news_bonus']} (Duygu: %{pick['news_sentiment']})",
                            f"+{pick['reversal_bonus']}",
                            f"+{pick.get('takas_bonus', 0)} (Pay: %{pick.get('takas_ratio', 0):.1f} | Değ: {pick.get('takas_change', 0):+.2f})"
                        ]
                    }
                    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
                    
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
                            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.warning("⚠️ **Yasal Uyarı:** Bu sonuçlar teknik ve istatistiksel analize dayanmaktadır. Kesinlikle yatırım tavsiyesi niteliği taşımaz.")

    elif mode == "⚠️ Risk Yönetim Merkezi":
        st.title("⚠️ Risk Yönetim Merkezi")
        st.caption("Pozisyon büyüklüğü hesaplama, ATR bazlı stop seviyeleri, Kelly Criterion ve portföy risk analizi.")
        
        risk_tab1, risk_tab2, risk_tab3, risk_tab4 = st.tabs([
            "📐 Pozisyon Hesaplayıcı", "🎯 ATR Stop/TP", "🏦 Portföy Risk Dashboard", "📊 Kelly Criterion"
        ])
        
        # --- TAB 1: Pozisyon Büyüklüğü Hesaplayıcı ---
        with risk_tab1:
            st.markdown("### 📐 Pozisyon Büyüklüğü Hesaplayıcı")
            st.markdown("Belirli bir risk yüzdesine göre kaç lot hisse alabileceğinizi hesaplayın.")
            
            ps_c1, ps_c2 = st.columns(2)
            with ps_c1:
                ps_capital = st.number_input("💰 Toplam Sermaye (₺)", min_value=1000.0, value=100000.0, step=1000.0, key="ps_cap")
                ps_entry = st.number_input("📍 Giriş Fiyatı (₺)", min_value=0.01, value=50.0, step=0.10, key="ps_entry")
            with ps_c2:
                ps_risk = st.slider("⚡ Risk Yüzdesi (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5, key="ps_risk")
                ps_sl = st.number_input("🛡️ Stop-Loss Fiyatı (₺)", min_value=0.01, value=45.0, step=0.10, key="ps_sl")
            
            if st.button("🧮 Hesapla", key="btn_pos_size", type="primary"):
                if ps_entry > ps_sl:
                    pos_result = calculate_position_size(ps_capital, ps_risk, ps_entry, ps_sl)
                    
                    r1, r2, r3 = st.columns(3)
                    r1.metric("📦 Alınabilir Adet", f"{pos_result['position_size']:,} lot")
                    r2.metric("💸 Toplam Yatırım", f"{pos_result['total_investment']:,.2f} ₺")
                    r3.metric("🔒 Max Risk Tutarı", f"{pos_result['max_risk_amount']:,.2f} ₺")
                    
                    st.markdown(f"""
                        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #38bdf8; margin-top: 10px;">
                            <b style="color: #38bdf8;">📊 Detaylı Özet:</b><br>
                            <span style="color: #cbd5e1;">• Hisse Başı Risk: <b>{pos_result['risk_per_share']:.2f} ₺</b></span><br>
                            <span style="color: #cbd5e1;">• Portföy Payı: <b>%{pos_result['portfolio_allocation_pct']:.1f}</b></span><br>
                            <span style="color: #cbd5e1;">• Risk / Sermaye: <b>%{ps_risk}</b> = <b>{pos_result['max_risk_amount']:,.2f} ₺</b></span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("⚠️ Giriş fiyatı, Stop-Loss fiyatından yüksek olmalıdır.")
        
        # --- TAB 2: ATR Stop/TP Hesaplayıcı ---
        with risk_tab2:
            st.markdown("### 🎯 ATR Bazlı Dinamik Stop-Loss / Take-Profit")
            st.markdown("Hissenin volatilitesine göre otomatik SL ve TP seviyeleri hesaplayın.")
            
            atr_sym = st.text_input("Hisse Kodu", "THYAO", key="atr_sym")
            atr_c1, atr_c2 = st.columns(2)
            with atr_c1:
                atr_sl_mult = st.slider("SL Çarpanı (x ATR)", 1.0, 5.0, 2.0, 0.5, key="atr_sl_m")
            with atr_c2:
                atr_tp_mult = st.slider("TP Çarpanı (x ATR)", 1.0, 8.0, 3.0, 0.5, key="atr_tp_m")
            
            if st.button("📊 ATR Hesapla", key="btn_atr", type="primary"):
                with st.spinner("Veriler yükleniyor..."):
                    atr_df = fetch_data(atr_sym, "1d", "6mo")
                if atr_df is not None and not atr_df.empty:
                    atr_result = calculate_atr_stops(atr_df, atr_sl_mult, atr_tp_mult)
                    if atr_result:
                        a1, a2, a3, a4 = st.columns(4)
                        a1.metric("📈 Güncel Fiyat", f"{atr_result['current_price']:.2f} ₺")
                        a2.metric("🔴 Stop-Loss", f"{atr_result['stop_loss']:.2f} ₺", f"-{atr_result['risk_per_share']:.2f} ₺")
                        a3.metric("🟢 Take-Profit", f"{atr_result['take_profit']:.2f} ₺", f"+{atr_result['reward_per_share']:.2f} ₺")
                        a4.metric("⚖️ R/R Oranı", f"{atr_result['risk_reward_ratio']:.2f}x")
                        
                        # Görsel bar
                        sl_pct = ((atr_result['current_price'] - atr_result['stop_loss']) / atr_result['current_price']) * 100
                        tp_pct = ((atr_result['take_profit'] - atr_result['current_price']) / atr_result['current_price']) * 100
                        
                        st.markdown(f"""
                            <div style="background-color: #1e293b; padding: 20px; border-radius: 10px; margin-top: 10px;">
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                                    <span style="color: #ff4757; font-weight: bold;">🔴 SL: {atr_result['stop_loss']:.2f}₺ (-%{sl_pct:.1f})</span>
                                    <span style="color: #38bdf8; font-weight: bold;">📍 Fiyat: {atr_result['current_price']:.2f}₺</span>
                                    <span style="color: #26de81; font-weight: bold;">🟢 TP: {atr_result['take_profit']:.2f}₺ (+%{tp_pct:.1f})</span>
                                </div>
                                <div style="display: flex; height: 20px; border-radius: 4px; overflow: hidden;">
                                    <div style="width: {sl_pct / (sl_pct + tp_pct) * 100:.0f}%; background: linear-gradient(90deg, #ff4757, #ff6b81);"></div>
                                    <div style="width: {tp_pct / (sl_pct + tp_pct) * 100:.0f}%; background: linear-gradient(90deg, #26de81, #2ed573);"></div>
                                </div>
                                <div style="text-align: center; margin-top: 8px; color: #94a3b8; font-size: 0.85rem;">ATR({14}): {atr_result['atr']:.4f} | Risk/Ödül: {atr_result['risk_reward_ratio']:.2f}x</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("ATR hesaplamak için yeterli veri bulunamadı.")
                else:
                    st.error("Veri çekilemedi.")
        
        # --- TAB 3: Portföy Risk Dashboard ---
        with risk_tab3:
            st.markdown("### 🏦 Portföy Risk Dashboard")
            
            risk_data = get_risk_dashboard_data(current_user)
            
            if risk_data['positions'].empty:
                st.info("📭 Portföyünüzde açık pozisyon bulunmuyor. Risk dashboard'u için önce hisse ekleyin.")
            else:
                rd1, rd2, rd3 = st.columns(3)
                rd1.metric("💰 Toplam Yatırım", f"{risk_data['total_invested']:,.2f} ₺")
                rd2.metric("🔴 Toplam VaR", f"{risk_data['total_var_amount']:,.2f} ₺")
                rd3.metric("📦 Pozisyon Sayısı", f"{len(risk_data['positions'])}")
                
                # Pozisyon Risk Detayları
                st.markdown("#### 📋 Pozisyon Bazlı Risk Detayları")
                pos_df = risk_data['positions'][['ticker', 'adet', 'alis_fiyati', 'sl', 'tp', 'var']].copy()
                pos_df.columns = ['Hisse', 'Adet', 'Maliyet (₺)', 'Stop-Loss (₺)', 'Take-Profit (₺)', 'Risk (VaR) ₺']
                st.dataframe(pos_df, use_container_width=True, hide_index=True)
                
                # Korelasyon Matrisi
                if not risk_data['correlation_matrix'].empty:
                    st.markdown("#### 🔗 Portföy Korelasyon Matrisi")
                    st.caption("Düşük korelasyon = iyi diversifikasyon. Yüksek korelasyon = aynı yönde hareket riski.")
                    
                    corr = risk_data['correlation_matrix']
                    
                    # Heatmap renklendirme
                    def color_corr(val):
                        if val >= 0.7: return 'background-color: #641e16; color: white; font-weight: bold'
                        elif val >= 0.4: return 'background-color: #b7950b; color: black'
                        elif val <= -0.3: return 'background-color: #1a5276; color: white'
                        else: return 'background-color: #0b5345; color: white'
                    
                    st.dataframe(corr.style.map(color_corr).format("{:.3f}"), use_container_width=True)
                    
                    avg_corr = corr.values[np.triu_indices_from(corr.values, k=1)].mean() if len(corr) > 1 else 0
                    if avg_corr > 0.6:
                        st.warning(f"⚠️ Ortalama korelasyon yüksek ({avg_corr:.2f}). Portföyünüz yeterince çeşitlendirilmemiş olabilir.")
                    else:
                        st.success(f"✅ Ortalama korelasyon makul ({avg_corr:.2f}). Portföy diversifikasyonu iyi durumda.")
        
        # --- TAB 4: Kelly Criterion ---
        with risk_tab4:
            st.markdown("### 📊 Kelly Criterion Hesaplayıcı")
            st.markdown("Geçmiş işlem performansınıza göre optimum pozisyon büyüklüğünüzü hesaplayın.")
            
            kc1, kc2 = st.columns(2)
            with kc1:
                k_wr = st.slider("🎯 Kazanma Oranı (%)", 10.0, 90.0, 55.0, 1.0, key="k_wr")
                k_avgwin = st.number_input("💚 Ortalama Kazanç (%)", min_value=0.1, value=5.0, step=0.5, key="k_avgwin")
            with kc2:
                k_avgloss = st.number_input("❌ Ortalama Kayıp (%)", min_value=0.1, value=3.0, step=0.5, key="k_avgloss")
                k_capital = st.number_input("💰 Sermaye (₺)", min_value=1000.0, value=100000.0, step=1000.0, key="k_cap")
            
            if st.button("📊 Kelly Hesapla", key="btn_kelly", type="primary"):
                kelly = calculate_kelly_criterion(k_wr, k_avgwin, k_avgloss)
                
                kk1, kk2, kk3 = st.columns(3)
                kk1.metric("🎯 Tam Kelly", f"%{kelly['kelly_pct']:.1f}")
                kk2.metric("⚖️ Yarım Kelly (Önerilen)", f"%{kelly['half_kelly_pct']:.1f}")
                kk3.metric("🛡️ Çeyrek Kelly (Güvenli)", f"%{kelly['quarter_kelly_pct']:.1f}")
                
                # Tutarları göster
                full_amount = k_capital * kelly['kelly_pct'] / 100
                half_amount = k_capital * kelly['half_kelly_pct'] / 100
                quarter_amount = k_capital * kelly['quarter_kelly_pct'] / 100
                
                st.markdown(f"""
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #c084fc; margin-top: 10px;">
                        <b style="color: #c084fc;">💡 Kelly Criterion Önerisi:</b><br>
                        <span style="color: #cbd5e1;">• Tam Kelly ile yatırılacak tutar: <b>{full_amount:,.2f} ₺</b></span><br>
                        <span style="color: #cbd5e1;">• <b style="color: #26de81;">Yarım Kelly (Önerilen):</b> <b>{half_amount:,.2f} ₺</b></span><br>
                        <span style="color: #cbd5e1;">• Çeyrek Kelly (Ultra Güvenli): <b>{quarter_amount:,.2f} ₺</b></span><br>
                        <span style="color: #94a3b8; font-size: 0.8rem;">Payoff Ratio (R): {kelly['payoff_ratio']:.2f}x</span>
                    </div>
                """, unsafe_allow_html=True)
                
                if kelly['kelly_pct'] <= 0:
                    st.error("🚫 Kelly Criterion negatif! Bu parametrelerle işlem yapmak istatistiksel olarak zararlıdır. Stratejiyi iyileştirin.")
                elif kelly['kelly_pct'] > 25:
                    st.warning("⚠️ Tam Kelly çok agresif! Yarım Kelly veya Çeyrek Kelly kullanmanız önerilir.")
    
    # ============================================================
    # 🔔 ALARM MERKEZİ
    # ============================================================
    elif mode == "🔔 Alarm Merkezi":
        st.title("🔔 Alarm Merkezi")
        st.caption("Fiyat, RSI, SMA kesişimi, hacim patlaması ve destek kırılımı alarmları oluşturun ve takip edin.")
        
        # Otomatik alarm kontrolü (sayfa her açıldığında)
        triggered_alerts = check_alerts(current_user)
        if triggered_alerts:
            for t_alert in triggered_alerts:
                st.toast(t_alert['message'], icon="🚨")
            st.success(f"🚨 {len(triggered_alerts)} alarm tetiklendi! Detaylar aşağıda.")
        
        alarm_tab1, alarm_tab2, alarm_tab3 = st.tabs(["➕ Yeni Alarm", "🟢 Aktif Alarmlar", "📜 Alarm Geçmişi"])
        
        # --- TAB 1: Yeni Alarm Oluştur ---
        with alarm_tab1:
            st.markdown("### ➕ Yeni Alarm Oluştur")
            
            al_c1, al_c2 = st.columns(2)
            with al_c1:
                al_ticker = st.text_input("Hisse Kodu", "THYAO", key="al_ticker").upper()
                al_type = st.selectbox(
                    "Alarm Tipi",
                    options=get_alert_type_options(),
                    format_func=lambda x: ALERT_TYPES[x],
                    key="al_type"
                )
            with al_c2:
                al_threshold = st.number_input(
                    get_threshold_label(al_type),
                    min_value=0.01,
                    value=get_default_threshold(al_type),
                    step=0.5,
                    key="al_threshold"
                )
                al_note = st.text_input("Not (İsteğe bağlı)", "", key="al_note")
            
            if st.button("🔔 Alarm Oluştur", key="btn_create_alert", type="primary"):
                alert_id = create_alert(current_user, al_ticker, al_type, al_threshold, al_note)
                st.success(f"✅ Alarm #{alert_id} başarıyla oluşturuldu! ({al_ticker} - {ALERT_TYPES[al_type]})")
                st.rerun()
        
        # --- TAB 2: Aktif Alarmlar ---
        with alarm_tab2:
            st.markdown("### 🟢 Aktif Alarmlar")
            
            active_df = get_active_alerts(current_user)
            if active_df.empty:
                st.info("📭 Aktif alarmınız bulunmuyor. Yeni bir alarm oluşturun.")
            else:
                # Tablo hazırla
                display_df = active_df[['id', 'ticker', 'alert_type', 'threshold', 'note', 'created_at']].copy()
                display_df['alert_type'] = display_df['alert_type'].apply(get_alert_type_label)
                display_df.columns = ['ID', 'Hisse', 'Alarm Tipi', 'Eşik', 'Not', 'Oluşturulma']
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Alarm silme
                del_c1, del_c2 = st.columns([2, 1])
                with del_c1:
                    del_id = st.selectbox("Silinecek Alarm ID", active_df['id'].tolist(), key="del_alarm_id")
                with del_c2:
                    st.write("")  # Spacing
                    if st.button("🗑️ Alarmı Sil", key="btn_del_alert"):
                        delete_alert(del_id)
                        st.success(f"Alarm #{del_id} silindi.")
                        st.rerun()
                
                # Manuel kontrol butonu
                if st.button("🔄 Alarmları Şimdi Kontrol Et", key="btn_check_alerts"):
                    with st.spinner("Aktif alarmlar kontrol ediliyor..."):
                        results = check_alerts(current_user)
                    if results:
                        for r in results:
                            st.warning(r['message'])
                    else:
                        st.info("✅ Tetiklenen alarm yok. Tüm koşullar henüz sağlanmadı.")
        
        # --- TAB 3: Alarm Geçmişi ---
        with alarm_tab3:
            st.markdown("### 📜 Tetiklenmiş Alarm Geçmişi")
            
            history_df = get_alert_history(current_user)
            if history_df.empty:
                st.info("📭 Henüz tetiklenmiş alarm bulunmuyor.")
            else:
                hist_display = history_df[['id', 'ticker', 'alert_type', 'threshold', 'triggered_value', 'triggered_at', 'note']].copy()
                hist_display['alert_type'] = hist_display['alert_type'].apply(get_alert_type_label)
                hist_display.columns = ['ID', 'Hisse', 'Alarm Tipi', 'Eşik', 'Tetikleme Değeri', 'Tetiklenme Zamanı', 'Not']
                
                st.dataframe(hist_display, use_container_width=True, hide_index=True)
    
    # ============================================================
    # 🧪 STRATEJİ KARŞILAŞTIRMA MOTORU
    # ============================================================
    elif mode == "🧪 Strateji Karşılaştırma Motoru":
        st.title("🧪 Strateji Karşılaştırma Motoru")
        st.caption("5 farklı trading stratejisini aynı hisse üzerinde geriye dönük test edin ve en iyi stratejiyi keşfedin.")
        
        sc_c1, sc_c2, sc_c3 = st.columns([1, 1, 1])
        with sc_c1:
            sc_sym = st.text_input("Hisse Kodu", "THYAO", key="sc_sym")
        with sc_c2:
            sc_period = st.selectbox("Backtest Periyodu", ["6 Ay", "1 Yıl", "2 Yıl"], index=1, key="sc_period")
        with sc_c3:
            period_map = {"6 Ay": "6mo", "1 Yıl": "1y", "2 Yıl": "2y"}
            sc_capital = st.number_input("Sermaye (₺)", min_value=10000.0, value=100000.0, step=10000.0, key="sc_cap")
        
        sc_strategies = st.multiselect(
            "Karşılaştırılacak Stratejiler",
            options=list(STRATEGY_NAMES.keys()),
            default=list(STRATEGY_NAMES.keys()),
            format_func=lambda x: STRATEGY_NAMES[x],
            key="sc_strats"
        )
        
        if st.button("🚀 Karşılaştırmayı Başlat", key="btn_compare", type="primary"):
            if not sc_strategies:
                st.error("En az bir strateji seçin.")
            else:
                with st.spinner(f"{sc_sym.upper()} üzerinde {len(sc_strategies)} strateji test ediliyor..."):
                    sc_df = fetch_data(sc_sym, "1d", period_map[sc_period])
                
                if sc_df is None or sc_df.empty or len(sc_df) < 60:
                    st.error("Backtest için yeterli veri bulunamadı. Farklı bir hisse veya daha kısa periyot deneyin.")
                else:
                    with st.spinner("Stratejiler çalıştırılıyor (bu işlem biraz sürebilir)..."):
                        comparison_df = compare_strategies(sc_df, sc_strategies, sc_capital)
                    
                    if comparison_df.empty:
                        st.error("Strateji sonuçları üretilemedi.")
                    else:
                        # En İyi Strateji Kartı
                        best = get_best_strategy(comparison_df)
                        
                        st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #0f172a, #1e293b); padding: 20px; border-radius: 12px; 
                                        border: 2px solid #26de81; margin-bottom: 20px;">
                                <div style="display: flex; align-items: center; gap: 15px;">
                                    <div style="font-size: 2.5rem;">🏆</div>
                                    <div>
                                        <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Bu Hisse İçin En İyi Strateji</div>
                                        <div style="color: #26de81; font-size: 1.5rem; font-weight: 900; margin-top: 4px;">{best['strategy']}</div>
                                        <div style="color: #cbd5e1; font-size: 0.9rem; margin-top: 6px;">{best['reason']}</div>
                                        <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 4px;">Genel Skor: <b style="color: #38bdf8;">{best['score']}/100</b></div>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Karşılaştırma Tablosu
                        st.markdown("### 📊 Strateji Performans Karşılaştırması")
                        
                        def style_comparison(row):
                            styles = [''] * len(row)
                            for i, col in enumerate(comparison_df.columns):
                                val = row[col]
                                if col == 'Toplam Getiri (%)':
                                    if isinstance(val, (int, float)):
                                        if val > 0: styles[i] = 'color: #26de81; font-weight: bold'
                                        else: styles[i] = 'color: #ff4757; font-weight: bold'
                                elif col == 'Sharpe Oranı':
                                    if isinstance(val, (int, float)):
                                        if val > 1.5: styles[i] = 'color: #26de81; font-weight: bold'
                                        elif val < 0: styles[i] = 'color: #ff4757; font-weight: bold'
                                elif col == 'Kazanma Oranı (%)':
                                    if isinstance(val, (int, float)):
                                        if val >= 60: styles[i] = 'color: #26de81; font-weight: bold'
                                        elif val < 40: styles[i] = 'color: #ff4757; font-weight: bold'
                                elif col == 'Maks Düşüş (%)':
                                    if isinstance(val, (int, float)):
                                        if val > 20: styles[i] = 'color: #ff4757; font-weight: bold'
                                        elif val < 10: styles[i] = 'color: #26de81; font-weight: bold'
                                elif col == 'Kâr Faktörü':
                                    if isinstance(val, (int, float)):
                                        if val >= 2.0: styles[i] = 'color: #26de81; font-weight: bold'
                                        elif val < 1.0: styles[i] = 'color: #ff4757; font-weight: bold'
                            return styles
                        
                        st.dataframe(
                            comparison_df.style.apply(style_comparison, axis=1).format(precision=2),
                            use_container_width=True,
                            hide_index=True,
                            height=300
                        )
                        
                        # Radar/Spider Chart — Strateji Güçlü/Zayıf Yönleri
                        st.markdown("### 🕸️ Strateji Radar Grafiği")
                        import plotly.graph_objects as go
                        
                        categories = ['Getiri', 'Sharpe', 'Win Rate', 'Düşük DD', 'Kâr Faktörü']
                        
                        fig_radar = go.Figure()
                        
                        for _, row in comparison_df.iterrows():
                            # Normalize (0-100 arası)
                            r_getiri = min(max(row.get('Toplam Getiri (%)', 0), -50), 100) / 100 * 100
                            r_getiri = max(r_getiri, 0)
                            r_sharpe = min(max(row.get('Sharpe Oranı', 0), 0), 3) / 3 * 100
                            r_wr = row.get('Kazanma Oranı (%)', 0)
                            r_dd = max(0, 100 - row.get('Maks Düşüş (%)', 0) * 2)  # Düşük DD = yüksek skor
                            r_pf = min(max(row.get('Kâr Faktörü', 0), 0), 5) / 5 * 100
                            
                            values = [r_getiri, r_sharpe, r_wr, r_dd, r_pf]
                            
                            fig_radar.add_trace(go.Scatterpolar(
                                r=values + [values[0]],  # Kapalı çokgen
                                theta=categories + [categories[0]],
                                fill='toself',
                                name=row['Strateji'],
                                opacity=0.6
                            ))
                        
                        fig_radar.update_layout(
                            polar=dict(
                                bgcolor='#0f172a',
                                radialaxis=dict(visible=True, range=[0, 100], gridcolor='#334155'),
                                angularaxis=dict(gridcolor='#334155')
                            ),
                            template='plotly_dark',
                            height=500,
                            showlegend=True,
                            title=f"{sc_sym.upper()} — Strateji Güç Haritası"
                        )
                        
                        st.plotly_chart(fig_radar, use_container_width=True)
                        
                        # Skor Tablosu
                        if best.get('all_scores'):
                            st.markdown("### 🏅 Genel Skor Tablosu")
                            score_df = pd.DataFrame([
                                {'Strateji': k, 'Genel Skor': v}
                                for k, v in sorted(best['all_scores'].items(), key=lambda x: x[1], reverse=True)
                            ])
                            
                            for _, srow in score_df.iterrows():
                                score_val = srow['Genel Skor']
                                bar_color = '#26de81' if score_val >= 50 else ('#fed330' if score_val >= 30 else '#ff4757')
                                medal = '🥇' if _ == 0 else ('🥈' if _ == 1 else ('🥉' if _ == 2 else '▫️'))
                                st.markdown(f"""
                                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                                        <span style="font-size: 1.2rem; min-width: 30px;">{medal}</span>
                                        <span style="color: #cbd5e1; min-width: 250px; font-weight: 600;">{srow['Strateji']}</span>
                                        <div style="flex: 1; height: 24px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                                            <div style="width: {score_val}%; height: 100%; background: {bar_color}; 
                                                        display: flex; align-items: center; justify-content: center;
                                                        font-size: 0.8rem; font-weight: bold; color: #0f172a;">{score_val:.0f}</div>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                        
                        st.warning("⚠️ **Not:** Geçmiş performans gelecekteki sonuçları garanti etmez. Piyasa koşulları değiştikçe strateji etkinliği de değişir.")
    
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
