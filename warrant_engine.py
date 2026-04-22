import numpy as np
from scipy.stats import norm

# Varant Analiz Modülü - Kantitatif Motor (Black-Scholes)

class WarrantEngine:
    """
    Black-Scholes modelini kullanarak varant teorik fiyatı ve 
    Delta, Gamma, Theta, Vega, Rho parametrelerini hesaplar.
    """
    
    @staticmethod
    def black_scholes(S, K, T, r, sigma, option_type='call'):
        """
        S: Dayanak Varlık Fiyatı
        K: Kullanım Fiyatı (Strike)
        T: Vadeye Kalan Süre (Yıl cinsinden)
        r: Risksiz Faiz Oranı (Yıllık)
        sigma: Volatilite (Zımni Oynaklık)
        """
        # Sıfır bölme kontrolü
        if T <= 0:
            return S - K if option_type == 'call' else K - S
            
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
        return price

    @staticmethod
    def calculate_greeks(S, K, T, r, sigma, option_type='call'):
        """
        Varant risk parametrelerini (Greeks) hesaplar.
        """
        T = max(T, 1e-6) # Yazılım hatasından kaçınma
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
            
        # Gamma
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Vega
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100 # %1'lik volatilite değişimi için
        
        # Theta (Günlük bazda)
        if option_type == 'call':
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
            
        # Rho
        if option_type == 'call':
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
            
        return {
            "delta": round(delta, 3),
            "gamma": round(gamma, 6),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
            "rho": round(rho, 4)
        }

    @staticmethod
    def score_warrant(S, p_market, p_theoretical, greeks, t_days, multiplier, leverage):
        """
        Kullanıcının 'En İyi Varant'ı bulması için skorlama algoritması.
        """
        score = 50 # Baz puan
        
        # 1. Arbitraj/Teorik Fiyat Uyumu (%20 etki)
        price_diff = (p_market - p_theoretical) / p_theoretical if p_theoretical > 0 else 1
        if abs(price_diff) < 0.05: score += 20 # Piyasa fiyatı teorik fiyata yakınsa güvenilir.
        elif price_diff < 0: score += 10 # İskontolu/Ucuz kalmış olabilir.
        
        # 2. Zaman Aşımı (Theta) Cezası (%30 etki)
        # Vadeye 10 günden az kaldıysa ağır ceza
        if t_days <= 10: score -= 40
        elif t_days <= 30: score -= 15
        
        # 3. Duyarlılık (Sensitivity)
        # Bir kademe değişim için gereken hisse hareketi
        # Delta ve Çarpan bazlı analiz
        delta = abs(greeks['delta'])
        sensitivity = p_market / (delta * multiplier) if delta > 0 else 999
        if sensitivity < 0.1: score += 15 # Çok hassas, hisse kıpırdasa yükselir.
        
        # 4. Kaldıraç Dengesi
        if 5 <= leverage <= 15: score += 15 # Optimal kaldıraç bölgesi
        
        return max(0, min(100, score))
    @staticmethod
    def get_top_warrants(warrant_list_df, get_price_func, r_rate=0.45):
        """
        Tüm varant listesini tarayarak en potansiyelli 'Star List' adaylarını seçer.
        """
        import pandas as pd
        from datetime import datetime
        
        results = []
        for _, row in warrant_list_df.iterrows():
            try:
                # 1. Dayanak Varlık Fiyatı
                underlying_price = get_price_func(row['underlying'])
                if underlying_price <= 0: continue
                
                # 2. Vade Analizi
                expiry = datetime.strptime(row['expiry_date'], '%Y-%m-%d')
                t_days = (expiry - datetime.now()).days
                t_years = t_days / 365
                
                # 3. Greeks & Teorik
                t_price = WarrantEngine.black_scholes(underlying_price, row['strike'], t_years, r_rate, row['iv'], row['type'].lower())
                greeks = WarrantEngine.calculate_greeks(underlying_price, row['strike'], t_years, r_rate, row['iv'], row['type'].lower())
                
                # 4. Market Fiyatı
                market_px = get_price_func(row['ticker'])
                if market_px <= 0: market_px = t_price # Simülasyon
                
                leverage = (abs(greeks['delta']) * underlying_price) / market_px if market_px > 0 else 0
                
                # 5. Skorlama
                score = WarrantEngine.score_warrant(underlying_price, market_px, t_price, greeks, t_days, row['multiplier'], leverage)
                
                results.append({
                    "Varant": row['ticker'],
                    "Dayanak": row['underlying'],
                    "Tip": row['type'],
                    "Skor": score,
                    "Delta": greeks['delta'],
                    "Kaldıraç": round(leverage, 1),
                    "Vade Gün": t_days,
                    "Durum": "GÜVENLİ" if score > 75 else "NORMAL" if score > 50 else "RİSKLİ"
                })
            except: continue
            
        if not results: return pd.DataFrame()
        
        full_df = pd.DataFrame(results).sort_values(by="Skor", ascending=False)
        return full_df.head(10) # En iyi 10 varantı paylaş
