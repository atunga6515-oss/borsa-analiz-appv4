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
