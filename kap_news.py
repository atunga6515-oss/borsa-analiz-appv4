import streamlit as st
import pandas as pd
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


def render_kap_news_panel():
    """
    KAP ve Medya Duygu Analizi (Sentiment Analysis) paneli.
    Google News RSS üzerinden hisse ile ilgili haberleri çeker,
    kelime bazlı duygu analizine tabi tutar ve sonuçları tablo + özet olarak sunar.
    """
    st.title("📰 KAP ve Haber Duygu Analizi")
    st.markdown("Şirketlere ait **KAP bildirimleri** ve **medya haberleri** toplanarak "
                "kelime bazlı **Duygu Analizine (Sentiment Analysis)** tabi tutulur. "
                "Böylece piyasanın hisse hakkındaki güncel pozitif/negatif algısı ölçülür.")

    # ----- Hisse Seçimi -----
    tck_base = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO", key="kap_sym").upper().strip()

    if not tck_base:
        return

    col_k1, col_k2 = st.columns([1, 2])

    with col_k1:
        st.info("📌 **KAP Resmi Bildirimlerine Hızlı Git**")
        kap_url = f"https://www.kap.org.tr/tr/arama/ozet/{tck_base}"
        st.markdown(f"**👉 [{tck_base} KAP Profilini Aç]({kap_url})**", unsafe_allow_html=True)

        st.divider()

        st.warning("🗞️ **Canlı Haber Analizini Başlat**")
        run_news = st.button("Haber Verilerini Çek & Analiz Et", type="primary", key="kap_btn")

    with col_k2:
        if run_news:
            with st.spinner("Haber kaynakları taranıyor ve kelime analizleri yapılıyor..."):
                query = urllib.parse.quote(f"{tck_base} hisse borsa")
                url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"

                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    resp = urllib.request.urlopen(req, timeout=10)
                    xml_data = resp.read()
                    root = ET.fromstring(xml_data)

                    # ---- Tarih Çevirici ----
                    def cevir_tarih(t_str):
                        if not t_str:
                            return ""
                        aylar = {"Jan": "Ocak", "Feb": "Şubat", "Mar": "Mart", "Apr": "Nisan",
                                 "May": "Mayıs", "Jun": "Haziran", "Jul": "Temmuz", "Aug": "Ağustos",
                                 "Sep": "Eylül", "Oct": "Ekim", "Nov": "Kasım", "Dec": "Aralık"}
                        gunler = {"Mon,": "Pazartesi,", "Tue,": "Salı,", "Wed,": "Çarşamba,",
                                  "Thu,": "Perşembe,", "Fri,": "Cuma,", "Sat,": "Cumartesi,",
                                  "Sun,": "Pazar,"}
                        for en, tr in gunler.items():
                            t_str = t_str.replace(en, tr)
                        for en, tr in aylar.items():
                            t_str = t_str.replace(en, tr)
                        return t_str.replace("GMT", "").strip()

                    # ---- Kelime Tabanlı Duygu Analizi ----
                    pozitif_kelimeler = [
                        'arttı', 'yüksel', 'kazanç', 'kar ', 'kâr', 'büyü', 'yatırım',
                        'anlaşma', 'temettü', 'olumlu', 'rekor', 'satın', 'ihale',
                        'pozitif', 'uçtu', 'artış', 'güçlü', 'başarı', 'ralli'
                    ]
                    negatif_kelimeler = [
                        'düştü', 'zarar', 'azaldı', 'küçülme', 'kriz', 'ceza', 'dava',
                        'iptal', 'olumsuz', 'düşüş', 'negatif', 'uyarı', 'risk',
                        'çakıldı', 'kayıp', 'geriledi', 'sert', 'endişe'
                    ]

                    analyzed = []
                    for item in root.findall('./channel/item')[:15]:
                        title = item.find('title').text
                        link = item.find('link').text
                        date_str = item.find('pubDate').text

                        title_lower = title.lower()
                        p_score = sum(1 for w in pozitif_kelimeler if w in title_lower)
                        n_score = sum(1 for w in negatif_kelimeler if w in title_lower)

                        if p_score > n_score:
                            duygu = "Pozitif 🟢"
                        elif n_score > p_score:
                            duygu = "Negatif 🔴"
                        else:
                            duygu = "Nötr ⚪"

                        analyzed.append({
                            "Haber Başlığı": title,
                            "Duygu Algısı": duygu,
                            "Tarih": cevir_tarih(date_str)
                        })

                    if analyzed:
                        df_n = pd.DataFrame(analyzed)

                        def c_duygu(val):
                            if 'Pozitif' in str(val):
                                return 'color: #26de81; font-weight: bold'
                            elif 'Negatif' in str(val):
                                return 'color: #fc5c65; font-weight: bold'
                            return 'color: #fed330'

                        try:
                            style_df = df_n.style.map(c_duygu, subset=['Duygu Algısı'])
                        except AttributeError:
                            style_df = df_n.style.applymap(c_duygu, subset=['Duygu Algısı'])

                        st.dataframe(style_df, use_container_width=True, hide_index=True)

                        p_cnt = len([x for x in analyzed if 'Pozitif' in x['Duygu Algısı']])
                        n_cnt = len([x for x in analyzed if 'Negatif' in x['Duygu Algısı']])
                        neu_cnt = len(analyzed) - p_cnt - n_cnt

                        # Özet Metrikler
                        st.markdown("---")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Pozitif Haber 🟢", p_cnt)
                        m2.metric("Negatif Haber 🔴", n_cnt)
                        m3.metric("Nötr Haber ⚪", neu_cnt)

                        st.write(f"**Sonuç:** Analiz edilen **{len(analyzed)}** haberin "
                                 f"**{p_cnt} tanesi Pozitif**, **{n_cnt} tanesi Negatif** algılanmıştır.")
                    else:
                        st.info("Hisseyle ilgili haber bulunamadı.")

                except Exception as e:
                    st.error("Haberlere erişimde sorun yaşandı: " + str(e))
