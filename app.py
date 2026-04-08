import streamlit as st
import pandas as pd
from data_loader import fetch_data, get_db_stats, clear_db, get_ticker_db_info, get_live_price
from indicators import calculate_indicators, generate_signals_and_score
from visualizations import create_advanced_chart, create_ml_chart, create_equity_curve_chart
from screener import (run_screener, BIST30_SYMBOLS, BIST100_SYMBOLS, BIST_ALL_SYMBOLS, 
                      save_scan_results, get_sector_list, filter_by_sector, 
                      get_scan_history, get_persistent_signals,
                      add_to_watchlist, remove_from_watchlist, get_watchlist)
from ml_forecast import generate_ml_forecast
from advanced_backtest import run_advanced_backtest
from support_resistance import calculate_best_zones
import portfolio as pf
import plotly.express as px
from kap_news import render_kap_news_panel
from top_picks import find_top_picks
import auth

# Kimlik doğrulama sistemini başlat
auth.init_auth_db()

st.set_page_config(page_title="BIST V4 Kurumsal Karar Destek", layout="wide", initial_sidebar_state="expanded")

def main():
    st.sidebar.title("BIST V4 🚀")
    
    # --- OTURUM YÖNETİMİ ---
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    if not st.session_state.logged_in:
        st.title("🔐 BIST V4 - Giriş Yap")
        with st.form("login_form"):
            u_input = st.text_input("Kullanıcı Adı (admin1, admin2, admin3)")
            p_input = st.text_input("Şifre", type="password")
            submitted = st.form_submit_button("Giriş")
            if submitted:
                if auth.verify_login(u_input, p_input):
                    st.session_state.logged_in = True
                    st.session_state.username = u_input
                    st.success(f"Hoş geldiniz, {u_input}!")
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre.")
        return # Giriş yapılana kadar alt tarafı gösterme

    # Giriş yapan kullanıcı bilgisi
    st.sidebar.markdown(f"👤 **Kullanıcı:** {st.session_state.username}")
    if st.sidebar.button("🚪 Çıkış Yap"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    current_user = st.session_state.username

    # Navigasyon
    mode = st.sidebar.radio("Modül Seçimi", [
        "1. Bireysel Hisse Analizi",
        "2. Canlı Tarayıcı (Screener)",
        "3. Yapay Zeka ML Tahmini",
        "4. Gelişmiş Backtest",
        "5. Sanal Portföy",
        "6. KAP ve Haberler",
        "7. 🏆 Haftalık Top 5 Öneri",
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

    

    if mode == "1. Bireysel Hisse Analizi":
        st.title("📊 Bireysel Hisse Analizi & Destek/Direnç")
        sym = st.sidebar.text_input("Hisse Kodu (Örn: EREGL)", "THYAO")
        if sym:
            with st.spinner("Veriler işleniyor..."):
                df = fetch_data(sym, "1d", "1y")
            if df.empty:
                st.error("Veri bulunamadı.")
                return
                
            df = calculate_indicators(df)
            res = generate_signals_and_score(df)
            sr_data = calculate_best_zones(df)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader(f"{sym.upper()} Genel Durum")
                st.info(f"**Karar:** {res['decision']} | **Skor:** {res['score']}")
                st.write(res['summary'])
                st.write("**Risk Yönetimi:**")
                st.write(f"- Stop Loss: {res['risk'].get('SL', 0):.2f}")
                st.write(f"- TP1 (%5): {res['risk'].get('TP1', 0):.2f}")
                
                # Destek & Direnç Tablosu
                if sr_data:
                    st.markdown("---")
                    st.subheader("🟢 En İyi Alım Bölgeleri (Destek)")
                    if sr_data.get('best_buy_zones'):
                        for label, val in sr_data['best_buy_zones']:
                            st.write(f"  ➡️ **{label}:** {val} ₺")
                    else:
                        st.write("Yakın destek bulunamadı.")
                    
                    st.subheader("🔴 En İyi Satım Bölgeleri (Direnç)")
                    if sr_data.get('best_sell_zones'):
                        for label, val in sr_data['best_sell_zones']:
                            st.write(f"  ➡️ **{label}:** {val} ₺")
                    else:
                        st.write("Yakın direnç bulunamadı.")
                    
                    with st.expander("📐 Fibonacci Seviyeleri"):
                        for name, val in sr_data.get('fibonacci', {}).items():
                            st.write(f"- **{name}:** {val} ₺")
                    
                    with st.expander("📊 Pivot Seviyeleri"):
                        pivots = sr_data.get('pivots', {})
                        for name, val in pivots.items():
                            st.write(f"- **{name}:** {val} ₺")

            with c2:
                fig = create_advanced_chart(df, sym.upper(), res['risk'], sr_data)
                st.plotly_chart(fig, use_container_width=True)

    elif mode == "2. Canlı Tarayıcı (Screener)":
        st.title("🔍 BIST Canlı Tarayıcı V2 (Screener)")
        
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
        
        custom_min_score = st.sidebar.slider("Min. Güven Skoru", 0, 100, 0)
        
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
                screener_df = screener_df[screener_df['Karar'] == 'Güçlü Al']
            elif filter_option == "Sadece Al":
                screener_df = screener_df[screener_df['Karar'].isin(['Al', 'Güçlü Al'])]
            elif filter_option == "Sadece Sat / Güçlü Sat":
                screener_df = screener_df[screener_df['Karar'].str.contains('Sat')]
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
                screener_df = screener_df[screener_df['Güven Skoru'] >= custom_min_score]
            
            if screener_df.empty:
                st.warning("Seçilen filtreye uyan hisse bulunamadı.")
            else:
                # Özellik 6: Günün Yıldızı Kartları
                st.markdown("---")
                k1, k2, k3 = st.columns(3)
                top_score = screener_df.iloc[0]
                k1.metric("🥇 Günün Yıldızı", f"{top_score['Hisse']}", f"Skor: {top_score['Güven Skoru']}")
                
                if 'Değişim (%)' in screener_df.columns:
                    best_gainer = screener_df.loc[screener_df['Değişim (%)'].idxmax()]
                    worst_loser = screener_df.loc[screener_df['Değişim (%)'].idxmin()]
                    k2.metric("📈 En Çok Yükselen", f"{best_gainer['Hisse']}", f"{best_gainer['Değişim (%)']}%")
                    k3.metric("📉 En Çok Düşen", f"{worst_loser['Hisse']}", f"{worst_loser['Değişim (%)']}%")
                
                st.markdown("---")
                
                # Renklendirme
                def style_all(row):
                    styles = [''] * len(row)
                    for i, col in enumerate(screener_df.columns):
                        val = row[col]
                        if col == 'Karar':
                            if 'Güçlü Al' in str(val): styles[i] = 'background-color: #2d6a2e; color: white'
                            elif val == 'Al': styles[i] = 'background-color: #1a5276; color: white'
                            elif 'Güçlü Sat' in str(val): styles[i] = 'background-color: #922b21; color: white'
                            elif 'Sat' in str(val): styles[i] = 'background-color: #b03a2e; color: white'
                        elif col == 'Değişim (%)':
                            if isinstance(val, (int, float)):
                                if val > 0: styles[i] = 'color: #00ff00; font-weight: bold'
                                elif val < 0: styles[i] = 'color: #ff4c4c; font-weight: bold'
                        elif col == '1D+1H Uyum':
                            if 'Çift AL' in str(val): styles[i] = 'background-color: rgba(45, 106, 46, 0.4)'
                            elif 'Çift SAT' in str(val): styles[i] = 'background-color: rgba(146, 43, 33, 0.4)'
                        elif col == 'Hacim Patlaması':
                            if 'Şoku' in str(val): styles[i] = 'background-color: rgba(0, 102, 204, 0.5); font-weight: bold'
                        elif col == 'Dipten Dönüş':
                            if 'Dönüş' in str(val): styles[i] = 'background-color: rgba(204, 102, 0, 0.5); font-weight: bold'
                    return styles
                
                st.success(f"Toplam {len(screener_df)} hisse listelendi.")
                st.dataframe(screener_df.style.apply(style_all, axis=1), use_container_width=True, height=600)
                
                # Özellik 3: CSV Export
                csv_data = screener_df.to_csv(index=False).encode('utf-8-sig')
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
                st.dataframe(persistent_df, use_container_width=True)
            else:
                st.info("Henüz birden fazla gün tarama geçmişi oluşmamış. Her gün tarama yaparak tutarlı sinyalleri burada göreceksiniz.")
        
        # ---- WATCHLIST (Özellik 8) ----
        with st.expander("🔔 İzleme Listem (Watchlist)"):
            wl_df = get_watchlist(current_user)
            if not wl_df.empty:
                st.dataframe(wl_df, use_container_width=True)
                wl_del = st.selectbox("Çıkarılacak Hisse:", wl_df['ticker'].tolist(), key="wl_del")
                if st.button("🗑️ İzleme Listesinden Çıkar"):
                    remove_from_watchlist(current_user, wl_del)
                    st.success(f"{wl_del} listeden çıkarıldı!")
                    st.rerun()
            else:
                st.info("İzleme listeniz boş. Tarama sonuçlarından hisse ekleyebilirsiniz.")


    elif mode == "3. Yapay Zeka ML Tahmini":
        st.title("🤖 Yapay Zeka (Makine Öğrenmesi) Fiyat Projeksiyonu")
        sym = st.sidebar.text_input("Hisse Kodu (Örn: EREGL)", "ASELS")
        days = st.sidebar.slider("Gelecek Tahmin Süresi (Gün)", 5, 60, 30)
        
        if sym:
            with st.spinner(f"{sym} için Machine Learning modeli eğitiliyor..."):
                df = fetch_data(sym, "1d", "3y") # Tahmin için uzun veri iyidir
                if df.empty:
                    st.error("Veri bulunamadı.")
                    return
                ml_result = generate_ml_forecast(df, days_ahead=days)
            
            if "error" in ml_result:
                st.error(ml_result["error"])
            else:
                st.subheader(f"Gelecek {days} İş Günü Tahmin Rotası")
                fig = create_ml_chart(df, ml_result, sym.upper())
                st.plotly_chart(fig, use_container_width=True)
                st.info("💡 Model, Polynomiyal Regresyon (Derece: 4) ve L2 Ridge optimizasyonu kullanarak geçmiş hareket paterni ve trend çizgisine göre istatistiksel bir 'olasılık konisi' çizer. Bu veriler finansal tavsiye niteliği taşımaz.")

    elif mode == "4. Gelişmiş Backtest":
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
                c1.metric("Nihai Portföy Değeri", f"₺{res['final_equity']:,.2f}", f"{res['total_return_pct']:.1f}%")
                c2.metric("Toplam İşlem Sayısı", f"{res['number_of_trades']}")
                c3.metric("Maksimum Kayıp (Drawdown)", f"{res['max_drawdown_pct']:.1f}%", delta_color="inverse")
                c4.metric("Al&Tut (Buy-Hold) Getirisi", f"{res['buy_and_hold_return_pct']:.1f}%")
                
                st.plotly_chart(create_equity_curve_chart(res['equity_curve'], sym.upper()), use_container_width=True)
                
                with st.expander("Detaylı İşlem Dökümü (Trades)"):
                    if res['trades']:
                        st.table(pd.DataFrame(res['trades']))
                    else:
                        st.write("Belirtilen süre zarfında AL/SAT sinyali üretilmedi.")

    elif mode == "5. Sanal Portföy":
        st.title("📈 Sanal Portföy Yönetimi")
        st.markdown("Beğendiğiniz hisseleri sanal olarak alıp, zaman içindeki başarınızı takip edebilirsiniz.")

        with st.expander("➕ Yeni Alım Ekle"):
            c1, c2, c3 = st.columns(3)
            with c1:
                t_sym = st.text_input("Hisse Kodu", "EREGL").upper()
            
            # Dinamik Fiyat Yakalama
            oto_fiyat = 50.0
            if t_sym:
                lv = get_live_price(t_sym)
                if lv > 0:
                    oto_fiyat = lv

            with c2:
                t_adet = st.number_input("Adet", min_value=0.1, value=10.0)
            with c3:
                t_fiyat = st.number_input("Alış Fiyatı (₺)", min_value=0.01, value=float(oto_fiyat))
            t_not = st.text_area("Not (Opsiyonel)", "")
            if st.button("Portföye Ekle"):
                pf.alis_yap(current_user, t_sym, t_adet, t_fiyat, t_not)
                st.success(f"{t_sym} portföye eklendi!")
                st.rerun()

        # Açık Pozisyonlar
        c_hdr1, c_hdr2 = st.columns([3, 1])
        with c_hdr1:
            st.subheader("🏁 Açık Pozisyonlar")
        with c_hdr2:
            if st.button("🔄 Canlı Fiyatları Yenile", use_container_width=True):
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
                    
                    p_data.append({
                        "ID": row['id'],
                        "Hisse": row['ticker'],
                        "Adet": row['adet'],
                        "Maliyet (₺)": round(row['alis_fiyati'], 2),
                        "Güncel (₺)": round(curr_price, 2),
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
            
            st.dataframe(p_df.style.applymap(highlight_pnl, subset=['Kâr/Zarar (₺)', 'Değişim (%)']), use_container_width=True)
            
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
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with gc2:
                st.subheader("📊 Hisse Bazlı Kar/Zarar")
                p_df_sorted = p_df.sort_values('Kâr/Zarar (₺)', ascending=False)
                fig_bar = px.bar(p_df_sorted, x='Hisse', y='Kâr/Zarar (₺)', color='Değişim (%)',
                                 title='Hisse Bazlı Kazanç Durumu', template='plotly_dark',
                                 color_continuous_scale=['red', 'yellow', 'green'],
                                 color_continuous_midpoint=0)
                st.plotly_chart(fig_bar, use_container_width=True)

            # İşlem Kapatma
            st.markdown("---")
            with st.expander("🛑 İşlemi Kapat (Sat)"):
                trade_to_close = st.selectbox("Kapatılacak İşlem ID", p_df['ID'].tolist())
                # Seçilen işlemin güncel fiyatını varsayılan yap
                current_p = p_df[p_df['ID']==trade_to_close]['Güncel (₺)'].iloc[0]
                satis_px = st.number_input("Satış Fiyatı (₺)", min_value=0.1, value=float(current_p))
                if st.button("İşlemi Kapat"):
                    pf.satis_yap(trade_to_close, satis_px)
                    st.success("İşlem kapatıldı!")
                    st.rerun()
        else:
            st.info("Henüz açık pozisyonunuz bulunmuyor.")

        # Geçmiş İşlemler
        st.subheader("📜 Geçmiş İşlemler")
        kapali_df = pf.kapali_pozisyonlar(current_user)
        if not kapali_df.empty:
            st.dataframe(kapali_df, use_container_width=True)
            
            with st.expander("🗑️ Geçmiş İşlemi Veritabanından Sil"):
                del_id = st.selectbox("Silinecek İşlem ID", kapali_df['id'].tolist(), key="del_kapali")
                if st.button("Kalıcı Olarak Sil"):
                    pf.islemi_sil(del_id)
                    st.success("İşlem başarıyla silindi!")
                    st.rerun()
        else:
            st.write("Kapatılmış işlem bulunmuyor.")

    elif mode == "6. KAP ve Haberler":
        render_kap_news_panel()

    elif mode == "7. 🏆 Haftalık Top 5 Öneri":
        st.title("🏆 Haftalık Yükselme Potansiyeli - Top 5 Öneri")
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
        
        if 'top_picks' in st.session_state and st.session_state['top_picks']:
            top_results = st.session_state['top_picks']
            
            st.markdown("---")
            st.subheader(f"🏆 Önümüzdeki 1 Hafta İçi Yükselme Potansiyeli En Yüksek {len(top_results)} Hisse")
            
            summary_data = []
            for r in top_results:
                summary_data.append({
                    "Hisse": r['ticker'],
                    "Sektör": r['sektor'],
                    "Fiyat (₺)": r['fiyat'],
                    "🎯 Kompozit Skor": r['kompozit_skor'],
                    "Teknik Skor": r['teknik_skor'],
                    "Karar": r['karar'],
                    "RSI": r['rsi'],
                    "Haber Duygusu": f"{r['news_sentiment']}%",
                    "Dipten Dönüş": r['reversal']
                })
            
            sum_df = pd.DataFrame(summary_data)
            
            def style_picks(row):
                styles = [''] * len(row)
                for i, col in enumerate(sum_df.columns):
                    val = row[col]
                    if col == '🎯 Kompozit Skor':
                        if val >= 70: styles[i] = 'background-color: #2d6a2e; color: white; font-weight: bold'
                        elif val >= 55: styles[i] = 'background-color: #1a5276; color: white'
                    elif col == 'Karar':
                        if 'Al' in str(val): styles[i] = 'color: #00ff00; font-weight: bold'
                        elif 'Sat' in str(val): styles[i] = 'color: #ff4c4c; font-weight: bold'
                return styles
            
            st.dataframe(sum_df.style.apply(style_picks, axis=1), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🔬 Detaylı Hisse Analizleri")
            
            import plotly.graph_objects as go
            for rank, pick in enumerate(top_results, 1):
                medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][rank-1] if rank <= 10 else f"{rank}."
                with st.expander(f"{medal} #{rank} - {pick['ticker']} | Kompozit Skor: {pick['kompozit_skor']} | {pick['fiyat']}₺", expanded=(rank <= 3)):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("🎯 Kompozit Skor", f"{pick['kompozit_skor']}/100")
                    m2.metric("📊 Teknik Skor", f"{pick['teknik_skor']}/100")
                    m3.metric("RSI (14)", pick['rsi'])
                    m4.metric("MACD Histogram", pick['macd_hist'])
                    
                    st.markdown("---")
                    st.write("**⚙️ Skor Bileşenleri & Bonus Puanlar:**")
                    comp_data = {
                        "Bileşen": ["📊 Teknik Analiz", "📈 Momentum", "🌊 Hacim", "⏰ Çoklu TF", 
                                   "🕯️ Formasyon", "🛡️ Destek", "📰 Haber", "🔥 Dipten Dönüş"],
                        "Ağırlık": ["%40", "%10", "%10", "%10", "%5", "%5", "%10", "%10"],
                        "Bonus Puan": [
                            f"{pick['teknik_skor']} (ana skor)",
                            f"+{pick['momentum_bonus']}",
                            f"+{pick['volume_bonus']}",
                            f"+{pick['tf_bonus']}",
                            f"+{pick['pattern_bonus']}",
                            f"+{pick['support_bonus']}",
                            f"+{pick['news_bonus']} (Duygu: %{pick['news_sentiment']})",
                            f"+{pick['reversal_bonus']}"
                        ]
                    }
                    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    r1, r2, r3 = st.columns(3)
                    risk = pick.get('risk_details', {})
                    r1.metric("Stop Loss", f"{risk.get('SL', '-')}₺")
                    r2.metric("Take Profit 1", f"{risk.get('TP1', '-')}₺")
                    r3.metric("Desteğe Uzaklık", f"%{pick['dist_support_pct']}" if pick['dist_support_pct'] != '-' else '-')
                    
                    s1, s2 = st.columns(2)
                    with s1:
                        st.write("**🕯️ Mum Formasyonu:**")
                        st.write(pick['pattern_text'])
                        st.write(f"**🔥 Dipten Dönüş:** {pick['reversal']}")
                    with s2:
                        st.write(f"**Dirençe Uzaklık:** %{pick['dist_resist_pct']}")
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
