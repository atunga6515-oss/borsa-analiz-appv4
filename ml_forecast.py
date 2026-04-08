import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import streamlit as st

@st.cache_data(ttl=300, show_spinner=False)
def generate_ml_forecast(df: pd.DataFrame, days_ahead: int = 20) -> dict:
    """
    Scikit-learn Polynomial Regression kullanarak fiyat için
    gelecek `days_ahead` kadar iş günü için tahmini fiyat rotası oluşturur.
    Geriye geçmişin fitted değerleri ve geleceğin tahmin değerlerini döndürür.
    """
    if df.empty or len(df) < 50:
         return {"error": "Tahmin için yeterli veri yok."}

    try:
        # Piyasalar haftasonu kapalıdır.
        # Basitlik adına Index'i nümerik (X) olarak alıp, Close fiyatını (y) hedefliyoruz.
        # Zaman serisinin sadece trend ve non-linear akışını tahmin etmeye çalışan bir ML modeli.
        data = df[['Close']].copy()
        data['Day'] = np.arange(len(data))
        
        X = data[['Day']]
        y = data['Close']

        # Polynomial Regression Pipeline (Degree=3 veya 4 fiyat hareketlerini iyi yakalar)
        # Ridge (L2 regularization) kullanıyoruz ki aşırı uca (overfitting) kaçmasın
        model = make_pipeline(PolynomialFeatures(degree=4), Ridge(alpha=1.0))
        model.fit(X, y)

        # Mevcut veriler üzerindeki fit (eğitilmiş eğriyi grafikte göstermek için)
        data['Predicted'] = model.predict(X)

        # Geleceği tasarlama (Future prediction)
        last_day = data['Day'].iloc[-1]
        future_days = np.arange(last_day + 1, last_day + 1 + days_ahead).reshape(-1, 1)
        future_preds = model.predict(future_days)
        
        # Gelecek için sahte Index oluştur (İş günlerini varsayarak)
        last_date = data.index[-1]
        future_dates = pd.bdate_range(start=last_date, periods=days_ahead + 1)[1:]

        future_df = pd.DataFrame({
            'Fiyat Tahmini': future_preds
        }, index=future_dates)

        # Calculate a simple confidence interval (standart sapma bazlı koni)
        residuals = y - data['Predicted']
        std_dev = np.std(residuals)

        future_df['Alt Bant'] = future_df['Fiyat Tahmini'] - (std_dev * 1.5)
        future_df['Üst Bant'] = future_df['Fiyat Tahmini'] + (std_dev * 1.5)

        return {
            "historical_fit": data['Predicted'],
            "future_dates": future_dates,
            "future_df": future_df,
            "std_dev": std_dev
        }

    except Exception as e:
        return {"error": f"ML Tahmin Hatası: {str(e)}"}
