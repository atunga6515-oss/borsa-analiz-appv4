import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
import streamlit as st
from data_loader import fetch_data

@st.cache_data(ttl=300, show_spinner=False)
def generate_ml_forecast(df: pd.DataFrame, days_ahead: int = 5) -> dict:
    """
    Random Forest Regressor kullanarak hibrit bir fiyat tahmini oluşturur.
    XU100 ve USDTRY verilerini dışsal özellik olarak dahil eder.
    """
    if df.empty or len(df) < 60:
         return {"error": "Tahmin için yeterli veri yok (En az 60 bar gerekli)."}

    try:
        data = df.copy()
        
        # --- EK ÖZELLİKLER (Eksogen Veriler) ---
        warnings = []
        try:
            xu100 = fetch_data("XU100", period="1y")
            usd = fetch_data("USDTRY=X", period="1y")
            
            if not xu100.empty:
                data = data.join(xu100[['Close']].rename(columns={'Close': 'XU100'}), how='left')
            else: warnings.append("⚠️ XU100 verisi eksik, model sadece fiyat analiziyle devam ediyor.")
            
            if not usd.empty:
                data = data.join(usd[['Close']].rename(columns={'Close': 'USD'}), how='left')
            else: warnings.append("⚠️ USDTRY verisi eksik, kur etkisi modele dahil edilemedi.")
            
            data = data.ffill().bfill()
        except Exception:
            warnings.append("⚠️ Dışsal veriler alınamadı, temel model kullanılıyor.")

        # Özellik Mühendisliği
        data['Day'] = np.arange(len(data))
        data['Day_of_Week'] = data.index.dayofweek
        
        features = ['Day', 'Day_of_Week']
        if 'RSI_14' in data.columns: features.append('RSI_14')
        if 'SMA_20' in data.columns:
            data['SMA20_Dist'] = (data['Close'] - data['SMA_20']) / data['SMA_20']
            features.append('SMA20_Dist')
        if 'XU100' in data.columns: features.append('XU100')
        if 'USD' in data.columns: features.append('USD')
        
        data = data.dropna(subset=features + ['Close'])
        X = data[features]
        y = data['Close']

        # Random Forest Model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)

        data['Predicted'] = model.predict(X)
        r2 = r2_score(y, data['Predicted'])
        
        # Geleceği Tasarla
        last_date = data.index[-1]
        future_dates = pd.bdate_range(start=last_date, periods=days_ahead + 1)[1:]
        
        future_X = pd.DataFrame({
            'Day': np.arange(len(data), len(data) + days_ahead),
            'Day_of_Week': future_dates.dayofweek,
            'RSI_14': [data['RSI_14'].iloc[-1]] * days_ahead,
            'SMA20_Dist': [data['SMA20_Dist'].iloc[-1] if 'SMA20_Dist' in data.columns else 0] * days_ahead
        })
        
        if 'XU100' in data.columns: future_X['XU100'] = [data['XU100'].iloc[-1]] * days_ahead
        if 'USD' in data.columns: future_X['USD'] = [data['USD'].iloc[-1]] * days_ahead
        
        future_X = future_X[features]
        future_preds = model.predict(future_X)
        
        future_df = pd.DataFrame({'Fiyat Tahmini': future_preds}, index=future_dates)

        # GÜVEN HUNİSİ (Standard Deviation Bands - Zamanla Genişleyen)
        residuals = y - data['Predicted']
        std_dev = np.std(residuals)
        
        # t-faktörü: Zaman ilerledikçe belirsizliğin artmasını simüle eder (sqrt(t))
        t_factors = np.sqrt(np.arange(1, days_ahead + 1))
        
        # 1 SD ve 2 SD kuşakları (Zamanla genişleyen huni)
        future_df['Alt Bant 1SD'] = future_df['Fiyat Tahmini'] - (std_dev * 1.0 * t_factors)
        future_df['Üst Bant 1SD'] = future_df['Fiyat Tahmini'] + (std_dev * 1.0 * t_factors)
        future_df['Alt Bant 2SD'] = future_df['Fiyat Tahmini'] - (std_dev * 2.0 * t_factors)
        future_df['Üst Bant 2SD'] = future_df['Fiyat Tahmini'] + (std_dev * 2.0 * t_factors)

        return {
            "historical_fit": data['Predicted'],
            "future_dates": future_dates,
            "future_df": future_df,
            "std_dev": std_dev,
            "confidence_score": round(max(0, min(100, r2 * 100)), 1),
            "warnings": warnings
        }

    except Exception as e:
        return {"error": f"ML Tahmin Hatası: {str(e)}"}
