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
        
        # 1. Temel verileri ROBŪST çek (Alternatif anahtarları dene)
        pe = info.get("trailingPE") or info.get("forwardPE") or 0
        pb = info.get("priceToBook") or 0
        eps = info.get("trailingEps") or info.get("forwardEps") or info.get("epsTrailingTwelveMonths") or 0
        bv = info.get("bookValue") or 0
        div_yield = info.get("dividendYield") or 0
        curr_price = info.get("currentPrice") or info.get("previousClose") or 0
        
        # Eğer BV yoksa ama fiyati ve PB'si varsa BV = Price / PB
        if not bv and pb and curr_price:
            bv = curr_price / pb

        # Sayısal dönüşümler
        pe = float(pe) if pe is not None else 0.0
        pb = float(pb) if pb is not None else 0.0
        eps = float(eps) if eps is not None else 0.0
        bv = float(bv) if bv is not None else 0.0
        div_yield = float(div_yield) * 100 if div_yield is not None else 0.0
        
        # Graham Sayısı (İçsel Değer) = sqrt(22.5 * EPS * BV)
        graham_value = 0.0
        if eps > 0 and bv > 0:
            graham_value = math.sqrt(22.5 * eps * bv)
            
        # Skorlama Sistemi (Robust)
        score = 50
        if 0 < pe <= 12: score += 20
        elif 12 < pe <= 25: score += 10
        elif pe > 45 or pe <= 0: score -= 15
        
        if 0 < pb <= 1.5: score += 20
        elif 1.5 < pb <= 4.0: score += 5
        elif pb > 10.0: score -= 20

        if div_yield > 4.0: score += 10
        
        score = max(0, min(100, score))
        
        # Durum Etiketleri
        durum = "Normal"
        if pb > 0 and pb < 1.1 and pe > 0 and pe < 12:
            durum = "Kelepir 💎"
        elif pb > 10 or pe > 40:
            durum = "Balon ⚠️"
        elif div_yield > 5.0:
            durum = "Emeklilik 🏖️"
        elif not pe and not pb:
             durum = "Veri Kısıtlı"
            
        return {
            "pe": round(pe, 2),
            "pb": round(pb, 2),
            "eps": round(eps, 2),
            "bv": round(bv, 2),
            "div_yield": round(div_yield, 2),
            "graham_value": round(graham_value, 2) if graham_value > 0 else "N/A",
            "fundamental_score": score,
            "status": durum
        }
        
    except Exception:
        return {
            "pe": 0.0, "pb": 0.0, "eps": 0.0, "bv": 0.0, "div_yield": 0.0,
            "graham_value": "N/A", "fundamental_score": 50, "status": "Veri Yok"
        }
