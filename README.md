# 🚀 BIST Borsa Analiz Uygulaması

**BIST Borsa Analiz Uygulaması**, Borsa İstanbul (BIST) pay piyasası için geliştirilmiş, kurumsal düzeyde veri analitiği, teknik analiz ve yapay zeka destekli tahmin yeteneklerine sahip profesyonel bir finansal terminaldir.

![Uygulama Preview](https://img.shields.io/badge/BIST-Financial_Terminal-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-yellow?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge&logo=streamlit)
![Version](https://img.shields.io/badge/Version-v3.0.0-brightgreen?style=for-the-badge)

---

## 🌟 Öne Çıkan Özellikler

### 1. 🛡️ Market Rejimi ve Adaptif Analiz
Uygulama, BIST 100 endeksini anlık takip ederek piyasanın **"Ayı"** veya **"Boğa"** modunda olduğunu tespit eder.
- **Ayı Piyasası:** RSI eşikleri ve hacim kriterleri otomatik olarak temkinli (conservative) moda çekilir. SMA 50 altı baskı filtrelenir.
- **Boğa Piyasası:** Momentum odaklı, agresif büyüme ve tavan avlama modülü devreye girer.

### 2. 🤖 101 İndikatörlü Ensemble Karar Motoru *(v3.0.0 — YENİ)*
Scikit-learn tabanlı ML modeline ek olarak, **101 adet benzersiz teknik indikatör kuralı** (SMA, EMA, WMA, KAMA, RSI, Stochastic, CCI, ROC, Bollinger, Keltner, Donchian, ADX, Aroon, MACD, MFI, VWAP vb.) üzerinden DRY mimaride çalışan bir **Ensemble Oylama Motoru** geliştirilmiştir.
- **Backtest Bazlı Adaptasyon:** Her indikatör hisse senedinin tarihsel verisi üzerinde bağımsız olarak test edilir; en yüksek başarı oranına sahip 15 indikatör seçilerek ağırlıklı oylama sistemine dahil edilir.
- **Hesaplama Süresi:** ~0.11 saniye (101 indikatör + 101 backtest + sıralama + oylama).

### 3. 🎯 Anlık Hamle ve Karar Terminali *(v3.0.0 — YENİ)*
Canlı AL/SAT/TUT önerileri sunan aksiyon odaklı bir karar paneli:
- **Canlı Hamle Önerisi:** Son sinyal durumuna göre net öneriler (ALIM YAPILABİLİR, TUT, SATIM YAP, NAKİTTE KAL).
- **Hareketli Ortalama Trend Analizi:** 20/50/52 günlük SMA ortalamalarına göre fiyat konumu analizi.

### 4. 🔍 Gelişmiş Screener + Ensemble Güven Skoru *(v3.0.0 — YENİ)*
Tüm BIST hisselerini saniyeler içinde tarayan paralel işleme motoru.
- **Ensemble Güven Skoru (0-100):** V6 Hibrit (%40) + Sinyal Güveni (%40) + Destek Yakınlığı (%20) + Çift AL/Akıllı Para bonusları.
- **Dinamik Sıralama:** Ensemble, V6, PGS ve Desteğe Yakınlık kriterlerine göre anlık tablo sıralama.
- Sektörel filtreleme, dipten dönüş, sıkışma, hacim patlaması gibi 10+ filtre.

### 5. ⚠️ Risk Yönetim Merkezi *(v3.0.0 — YENİ)*
Portföy bazlı risk analiz ve yönetim modülü:
- **Pozisyon Büyüklüğü Hesaplayıcı:** Sermaye ve risk yüzdesine göre kaç lot alınacağını hesaplar.
- **ATR Bazlı Stop/TP:** Volatiliteye dayalı dinamik Stop-Loss ve Take-Profit seviyeleri.
- **Kelly Criterion:** Optimum pozisyon büyüklüğünü istatistiksel formülle hesaplar (Tam, Yarım, Çeyrek Kelly).
- **Portföy Risk Dashboard:** Toplam VaR, korelasyon matrisi, pozisyon bazlı risk detayları.

### 6. 🔔 Alarm Merkezi *(v3.0.0 — YENİ)*
8 farklı alarm tipini destekleyen kalıcı bildirim sistemi:
- Fiyat Üstü/Altı, RSI Aşırı Alım/Satım, SMA Kesişimi, Hacim Patlaması, Destek Kırılımı.
- SQLite tabanlı kalıcı alarm depolama, otomatik tetikleme ve alarm geçmişi takibi.

### 7. 🧪 Strateji Karşılaştırma Motoru *(v3.0.0 — YENİ)*
5 farklı trading stratejisini aynı hisse üzerinde karşılaştıran backtest motoru:
- **Stratejiler:** Momentum, Mean Reversion, Breakout, MACD Crossover, Ensemble (101 İndikatör).
- **Metrikler:** Sharpe Ratio, Sortino Ratio, Win Rate, Max Drawdown, Kâr Faktörü.
- **Radar Grafiği:** Stratejilerin güçlü/zayıf yönlerini gösteren çokgen grafik.
- **Otomatik Öneri:** Hisse bazında en iyi strateji seçimi ve gerekçesi.

### 8. 🤖 Yapay Zeka (ML) Fiyat Projeksiyonu
Scikit-learn tabanlı **Polynomiyal Regresyon** ve **L2 Ridge** optimizasyonu ile hisse fiyatları için 20-60 günlük olasılık konileri oluşturulur.
- **Korelasyon Analizi:** Tahmin modeline Dolar/TL (USDTRY=X) ve Altın (GC=F) verileri ek özellik (feature) olarak dahil edilmiştir.

### 9. 📈 Sanal Portföy ve Backtest
- **Portföy:** Anlık fiyatlarla P&L takibi, maliyet analizi ve görsel dağılım grafikleri.
- **Backtest:** Geçmiş veriler üzerinde strateji simülasyonu, maksimum kayıp (Drawdown) ve Al-Tut karşılaştırması.

### 10. 🏆 Stratejik Seçki (Top Picks)
Haftalık bazda yükselme potansiyeli en yüksek hisseleri bulmak için 8 farklı boyutta ağırlıklı puanlama (Composite Scoring) yapılır.
- **Analiz Geçmişi:** Tüm Top 5 analiz sonuçları tarih bazlı olarak SQLite veritabanında saklanır.

---

## 🛠️ Kurulum

Uygulamayı yerel bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

1. **Depoyu klonlayun:**
   ```bash
   git clone https://github.com/kullanici/bist-analiz-uygulamasi.git
   cd bist-analiz-uygulamasi
   ```

2. **Gerekli kütüphaneleri yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Uygulamayı başlatın:**
   ```bash
   streamlit run app.py
   ```

---

## ⚙️ Teknik Yapı

- **Frontend:** Streamlit ile modern ve dinamik dashboard tasarımı.
- **Backend:** Python + Pandas + NumPy.
- **Veri Kaynağı:** yfinance API.
- **Teknik Analiz:** TA (Technical Analysis Library) — 101+ indikatör.
- **Yapay Zeka:** Scikit-learn (Ridge Regression, Polynomial Features).
- **Veritabanı:** SQLite (Veri önbellekleme, kullanıcı sistemi, portföy, alarmlar ve tarama geçmişi).
- **Görselleştirme:** Plotly (Mum grafik, radar chart, heatmap, equity curve).

---

## 📋 Versiyon Geçmişi

| Versiyon | Tarih | Değişiklikler |
|----------|-------|---------------|
| v3.0.0 | 2025-06 | 101 İndikatör Ensemble Motoru, Karar Terminali, Ensemble Sıralama, Risk Yönetim Merkezi, Alarm Merkezi, Strateji Karşılaştırma Motoru |
| v2.6.1 | 2025-05 | Hisse adı ve canlı fiyat kartı |
| v2.5.0 | 2025-04 | Gelişmiş Screener, Tarama Geçmişi, Sektör Filtreleri |
| v2.0.0 | 2025-03 | ML Forecast, Gelişmiş Backtest, Sanal Portföy |
| v1.0.0 | 2025-02 | İlk sürüm: Temel teknik analiz ve sinyal sistemi |

---

## 🔐 Güvenlik ve Çoklu Kullanıcı
Uygulama, SQLite tabanlı bir kimlik doğrulama sistemi içerir. Her kullanıcının izleme listesi (Watchlist), sanal portföyü, alarmları ve tarama geçmişi veritabanında izole edilerek güvenli bir şekilde saklanır.

---

## ⚠️ Yasal Uyarı
Bu uygulama yalnızca eğitim ve analiz amaçlıdır. Uygulama tarafından üretilen sinyaller, tahminler ve skorlar **kesinlikle yatırım tavsiyesi (YTD) niteliği taşımaz.** Finansal kararlarınızı vermeden önce SPK lisanslı bir yatırım danışmanına başvurun.

---

## 📝 Lisans
Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.

---
**Geliştirici:** Antigravity AI
