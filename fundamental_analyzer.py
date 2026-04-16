import streamlit as st
import yfinance as yf
import math
import time

@st.cache_data(ttl=3600*12, show_spinner=False)
def get_fundamental_data(ticker_symbol: str) -> dict:
    """Verilen hissenin temel analiz rasyolarını getirir. (Geliştirilmiş Robust Versiyon)"""
    try:
        tkr = ticker_symbol if ticker_symbol.endswith(".IS") else f"{ticker_symbol}.IS"
        ticker = yf.Ticker(tkr)
        
        # 1. RETRY LOGIC (Yfinance bazen boş dönebilir)
        info = {}
        for _ in range(2):
            info = ticker.info
            if info and len(info) > 10: break
            time.sleep(0.5)
        
        if not info: info = {}

        # 2. FALLBACK TO FAST_INFO
        fi = ticker.fast_info
        curr_price = info.get("currentPrice") or info.get("previousClose") or getattr(fi, 'last_price', 0)
        
        # 3. VERİ ÇEKİMİ
        pe = info.get("trailingPE") or info.get("forwardPE")
        pb = info.get("priceToBook") or info.get("priceToBookValue")
        eps = info.get("trailingEps") or info.get("forwardEps") or info.get("epsTrailingTwelveMonths")
        bv = info.get("bookValue") or getattr(fi, 'book_value', 0)
        
        div_yield = info.get("dividendYield")
        if div_yield is None:
            div_yield = info.get("yield") # Alternatif anahtar
            
        # 4. MATEMATİKSEL TAMAMLAMA (Eksik verileri türetme)
        # EPS varsa ama PE yoksa: PE = Price / EPS
        if (pe is None or pe == 0) and eps and eps != 0 and curr_price:
            pe = curr_price / eps
            
        # PB varsa ama BV yoksa: BV = Price / PB
        if (bv is None or bv == 0) and pb and pb != 0 and curr_price:
            bv = curr_price / pb
            
        # Price ve BV varsa ama PB yoksa: PB = Price / BV
        if (pb is None or pb == 0) and bv and bv != 0 and curr_price:
            pb = curr_price / bv

        # Sayısal Temizlik
        pe = float(pe) if pe is not None else 0.0
        pb = float(pb) if pb is not None else 0.0
        eps = float(eps) if eps is not None else 0.0
        bv = float(bv) if bv is not None else 0.0
        
        # Dividend Yield Ölçekleme (0.05 -> %5, ama 0.82 zaten %0.82 ise dokunma)
        if div_yield is not None:
            div_yield = float(div_yield)
            if div_yield < 0.15: # Sadece %15 altındaki 'decimal' formatları çarp (0.05 gibi)
                div_yield = div_yield * 100
        else:
            div_yield = 0.0
        
        # Graham Sayısı (İçsel Değer) = sqrt(22.5 * EPS * BV)
        graham_value = 0.0
        if eps > 0 and bv > 0:
            graham_value = math.sqrt(22.5 * eps * bv)
            
        # Skorlama Sistemi
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
        elif pb > 8 or pe > 40:
            durum = "Riskli ⚠️"
        elif div_yield > 5.0:
            durum = "Temettü Verimi 🏖️"
        elif pe == 0 or pb == 0:
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
