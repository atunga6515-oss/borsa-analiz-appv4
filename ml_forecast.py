import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import r2_score
import streamlit as st
from data_loader import fetch_data
import logging

# Prophet loglarını gizle (Streamlit temizliği için)
logging.getLogger('prophet').setLevel(logging.ERROR)
logging.getLogger('cmdstanpy').setLevel(logging.ERROR)

@st.cache_data(ttl=300, show_spinner=False)
def generate_ml_forecast(df: pd.DataFrame, days_ahead: int = 15) -> dict:
    """
    Meta Prophet kullanarak Log-Price tabanlı hibrit bir fiyat tahmini oluşturur.
    XU100 ve USDTRY verilerini exogenous regressor olarak dahil eder.
    """
    if df.empty or len(df) < 100:
         return {"error": "Tahmin için yeterli veri yok (Prophet için en az 100 bar, tercihen 1-2 yıl önerilir)."}

    try:
        data = df.copy()
        
        # --- EK ÖZELLİKLER (Exogenous Data) ---
        warnings = []
        try:
            # Kullanıcının 2 yıllık veri önerisine uyum sağlamak için dışsal verileri de geniş çekiyoruz
            xu100 = fetch_data("XU100", period="3y")
            usd = fetch_data("USDTRY=X", period="3y")
            
            if not xu100.empty:
                data = data.join(xu100[['Close']].rename(columns={'Close': 'XU100'}), how='left')
            else: warnings.append("⚠️ XU100 eksik, model sadece hisse trendiyle devam ediyor.")
            
            if not usd.empty:
                data = data.join(usd[['Close']].rename(columns={'Close': 'USD'}), how='left')
            else: warnings.append("⚠️ USDTRY eksik, kur etkileşimi devre dışı.")
            
            data = data.ffill().bfill()
        except Exception:
            warnings.append("⚠️ Dışsal veriler entegre edilemedi, yalın Prophet çalışıyor.")

        # Öneri 3: Stationarity - Log Price Dönüşümü
        # Fiyatları logaritmik uzaya taşıyarak varyansı stabilize ediyoruz.
        data['y'] = np.log(data['Close'])
        data['ds'] = data.index.tz_localize(None) # Saat dilimini kaldır (Prophet gereksinimi)
        
        # Prophet Hazırlığı
        # Öneri 2: Zaman Serisi Odaklı Model (Prophet)
        model = Prophet(
            daily_seasonality=False,   # Hafta sonu boşlukları ve günlük veri için False
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05 # Esneklik ayarı
        )
        
        # Türkiye Tatilleri Ekleme
        try:
            model.add_country_holidays(country_name='TR')
        except:
            pass
            
        # Exogenous Regressors
        if 'XU100' in data.columns:
            data['XU100_log'] = np.log(data['XU100'])
            model.add_regressor('XU100_log')
        if 'USD' in data.columns:
            data['USD_log'] = np.log(data['USD'])
            model.add_regressor('USD_log')

        # Eğitim
        train_df = data[['ds', 'y']].copy()
        if 'XU100_log' in data.columns: train_df['XU100_log'] = data['XU100_log']
        if 'USD_log' in data.columns: train_df['USD_log'] = data['USD_log']
        
        model.fit(train_df)
        
        # Tahmin Periyodu (Hafta sonlarını atlamak için freq='B')
        future = model.make_future_dataframe(periods=days_ahead, freq='B')
        
        # Regresörlerin gelecek değerlerini 'naive' (sabit) olarak ata
        if 'XU100_log' in data.columns:
            future['XU100_log'] = data['XU100_log'].iloc[-1]
        if 'USD_log' in data.columns:
            future['USD_log'] = data['USD_log'].iloc[-1]
            
        forecast = model.predict(future)
        
        # Logaritmik sonuçları gerçek fiyatlara geri döndür (exp)
        forecast['yhat_price'] = np.exp(forecast['yhat'])
        forecast['yhat_lower_price'] = np.exp(forecast['yhat_lower'])
        forecast['yhat_upper_price'] = np.exp(forecast['yhat_upper'])
        
        # Tarihsel Uyum ve R2
        historical_preds = forecast.set_index('ds').loc[data['ds'], 'yhat']
        r2 = r2_score(data['y'], historical_preds)
        
        # Gelecek Dataframe'i Oluştur
        future_df = forecast.tail(days_ahead).copy()
        future_df.set_index('ds', inplace=True)
        
        # API Çıktısı Formatına Dönüştür
        out_future = pd.DataFrame({
            'Fiyat Tahmini': future_df['yhat_price'],
            'Alt Bant 1SD': future_df['yhat_lower_price'], # Prophet'in %80 güven aralığı
            'Üst Bant 1SD': future_df['yhat_upper_price'],
            # 2SD simülasyonu (Aradaki mesafeyi genişleterek)
            'Alt Bant 2SD': np.exp(future_df['yhat'] - (future_df['yhat'] - future_df['yhat_lower']) * 1.5),
            'Üst Bant 2SD': np.exp(future_df['yhat'] + (future_df['yhat_upper'] - future_df['yhat']) * 1.5)
        })

        return {
            "historical_fit": pd.Series(np.exp(historical_preds.values), index=data.index),
            "future_dates": out_future.index,
            "future_df": out_future,
            "confidence_score": round(max(0, min(100, r2 * 100)), 1),
            "warnings": warnings,
            "model_type": "Prophet High-Performance Engine (Log-Scaled)"
        }

    except Exception as e:
        return {"error": f"Prophet Tahmin Hatası: {str(e)}"}
