import streamlit as st
import yfinance as yf
import math

@st.cache_data(ttl=3600*24, show_spinner=False)
def get_fundamental_data(ticker_symbol: str) -> dict:
    """Verilen hissenin temel analiz rasyolarını getirir."""
    try:
        # yfinance BIST hisselerinde genelde sonuna .IS alarak çalışır
        tkr = ticker_symbol if ticker_symbol.endswith(".IS") else f"{ticker_symbol}.IS"
        ticker = yf.Ticker(tkr)
        info = ticker.info
        
        # Temel verileri güvenli çek
        pe = info.get("trailingPE", 0)
        pb = info.get("priceToBook", 0)
        eps = info.get("trailingEps", 0)
        bv = info.get("bookValue", 0)
        div_yield = info.get("dividendYield", 0)
        
        # None gelirse düzelt
        pe = float(pe) if pe is not None else 0.0
        pb = float(pb) if pb is not None else 0.0
        eps = float(eps) if eps is not None else 0.0
        bv = float(bv) if bv is not None else 0.0
        div_yield = float(div_yield) * 100 if div_yield is not None else 0.0
        
        # Graham Sayısı (İçsel Değer) = sqrt(22.5 * EPS * BV)
        graham_value = 0.0
        if eps > 0 and bv > 0:
            graham_value = math.sqrt(22.5 * eps * bv)
            
        # Temel Analiz Skoru (0-100)
        # Basit bir puanlama: 
        # PE ne kadar düşükse o kadar iyi (Optimal 5-15 arası). PE < 0 ise zarar açıklıyor, 0 puan. PE > 50 ise şişik, 0 puan.
        # PB ne kadar düşükse o kadar iyi (Optimal 0.5 - 2 arası).
        # Dividend varlığı + puan.
        
        score = 50 # Ortalama başlangıç
        
        if 0 < pe <= 10:
            score += 20
        elif 10 < pe <= 20:
            score += 10
        elif pe > 40:
            score -= 20
        elif pe == 0:
            score -= 10 # Data yok veya zarar
            
        if 0 < pb <= 1.2:
            score += 20
        elif 1.2 < pb <= 3.0:
            score += 5
        elif pb > 8.0:
            score -= 20
            
        if div_yield > 4.0:
            score += 10 # Yüksek temettü
            
        # Skor Sınırlandırması
        score = max(0, min(100, score))
        
        # Durum Etiketleri
        durum = "Normal"
        if pb > 0 and pb < 1.1 and pe > 0 and pe < 10:
            durum = "Kelepir 💎"
        elif pb > 10 or pe > 35:
            durum = "Balon ⚠️"
        elif div_yield > 5.0:
            durum = "Emeklilik 🏖️"
            
        return {
            "pe": round(pe, 2),
            "pb": round(pb, 2),
            "eps": round(eps, 2),
            "bv": round(bv, 2),
            "div_yield": round(div_yield, 2),
            "graham_value": round(graham_value, 2),
            "fundamental_score": score,
            "status": durum
        }
        
    except Exception:
        # Data çekilemezse boş taslak yolla
        return {
            "pe": 0.0, "pb": 0.0, "eps": 0.0, "bv": 0.0, "div_yield": 0.0,
            "graham_value": 0.0, "fundamental_score": 50, "status": "Veri Yok"
        }
