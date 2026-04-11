# 🚀 BIST Borsa Analiz Uygulaması

**BIST Borsa Analiz Uygulaması**, Borsa İstanbul (BIST) pay piyasası için geliştirilmiş, kurumsal düzeyde veri analitiği, teknik analiz ve yapay zeka destekli tahmin yeteneklerine sahip profesyonel bir finansal terminaldir.

![Uygulama Preview](https://img.shields.io/badge/BIST-Financial_Terminal-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-yellow?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge&logo=streamlit)

---

## 🌟 Öne Çıkan Özellikler

### 1. 🛡️ Market Rejimi ve Adaptif Analiz
Uygulama, BIST 100 endeksini anlık takip ederek piyasanın **"Ayı"** veya **"Boğa"** modunda olduğunu tespit eder.
- **Ayı Piyasası:** RSI eşikleri ve hacim kriterleri otomatik olarak temkinli (conservative) moda çekilir. SMA 50 altı baskı filtrelenir.
- **Boğa Piyasası:** Momentum odaklı, agresif büyüme ve tavan avlama modülü devreye girer.

### 2. 🤖 Yapay Zeka (ML) Fiyat Projeksiyonu
Scikit-learn tabanlı **Polynomiyal Regresyon** ve **L2 Ridge** optimizasyonu ile hisse fiyatları için 20-60 günlük olasılık konileri oluşturulur.
- **Korelasyon Analizi:** Tahmin modeline Dolar/TL (USDTRY=X) ve Altın (GC=F) verileri ek özellik (feature) olarak dahil edilmiştir.

### 3. 🔬 Derinlemesine Teknik Analiz ve Top 5
Haftalık bazda yükselme potansiyeli en yüksek hisseleri bulmak için 8 farklı boyutta ağırlıklı puanlama (Composite Scoring) yapılır.
- **Analiz Geçmişi (YENİ):** Tüm Top 5 analiz sonuçları tarih bazlı olarak SQLite veritabanında saklanır. Kullanıcılar geçmiş haftalardaki başarı oranlarını ve önerileri geriye dönük inceleyebilir.
- **Teknik İndikatörler:** RSI, MACD, STOCH, SMA/EMA vb. (20+ indikatör)
- **Haber Duygu Analizi (Sentiment):** Google News üzerinden anlık haber tarama ve doğal dil işleme.
- **Candlestick Patterns:** Çekiç, Yutan Boğa vb. 10+ formasyonun otomatik tespiti.
- **Hacim Onayı:** Volatilite ve hacim patlaması (Volume Spike) analizi.

### 4. 🔍 Gelişmiş Screener (Tarayıcı)
Tüm BIST hisselerini saniyeler içinde tarayan paralel işleme motoru.
- Sektörel filtreleme.
- "Dipten Dönüş" ve "Çift AL (1D+1H)" gibi karmaşık sinyallere göre filtreleme.
- Tarama sonuçlarını CSV olarak indirme.

### 5. 📈 Sanal Portföy ve Backtest
- **Portföy:** Anlık fiyatlarla P&L takibi, maliyet analizi ve görsel dağılım grafikleri.
- **Backtest:** Geçmiş veriler üzerinde strateji simülasyonu, maksimum kayıp (Drawdown) ve Al-Tut karşılaştırması.

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
- **Teknik Analiz:** TA (Technical Analysis Library).
- **Yapay Zeka:** Scikit-learn (Ridge Regression, Polynomial Features).
- **Veritabanı:** SQLite (Veri önbellekleme, kullanıcı sistemi ve portföy yönetimi için).

---

## 🔐 Güvenlik ve Çoklu Kullanıcı
Uygulama, SQLite tabanlı bir kimlik doğrulama sistemi içerir. Her kullanıcının izleme listesi (Watchlist) ve sanal portföyü veritabanında izole edilerek güvenli bir şekilde saklanır.

---

## ⚠️ Yasal Uyarı
Bu uygulama yalnızca eğitim ve analiz amaçlıdır. Uygulama tarafından üretilen sinyaller, tahminler ve skorlar **kesinlikle yatırım tavsiyesi (YTD) niteliği taşımaz.** Finansal kararlarınızı vermeden önce SPK lisanslı bir yatırım danışmanına başvurun.

---

## 📝 Lisans
Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.

---
**Geliştirici:** Antigravity AI
