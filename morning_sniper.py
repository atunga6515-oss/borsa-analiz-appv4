import pandas as pd
from data_loader import fetch_data, get_live_price
from indicators import calculate_indicators, generate_signals_and_score, get_market_regime, check_volatility_squeeze
from kap_news import get_sentiment_summary
from support_resistance import calculate_best_zones
from screener import BIST100_SYMBOLS
import concurrent.futures

def get_morning_sniper_candidates(symbol_list=None):
    """
    Borsa açılışında patlama potansiyeli en yüksek 3-5 hisseyi bulur.
    """
    if symbol_list is None:
        symbol_list = BIST100_SYMBOLS

    xu100_df = fetch_data("XU100", "1d", "1mo")
    market_regime = get_market_regime(xu100_df)

    candidates = []

    def analyze_for_sniper(sym):
        try:
            df = fetch_data(sym, "1d", "6mo")
            if df.empty or len(df) < 30: return None
            
            df = calculate_indicators(df)
            live_px = get_live_price(sym)
            
            # 1. Haber Analizi (Overnight Sentiment)
            sent_score, news = get_sentiment_summary(sym)
            
            # 2. Squeeze Analizi
            sq_res = check_volatility_squeeze(df)
            
            # 3. Genel Skor
            sig = generate_signals_and_score(df, market_regime=market_regime, sentiment_score=sent_score)
            
            # SNIPER PUANLAMA (Bugünlük Trade Uygunluğu)
            # Squeeze varsa +30, Pozitif Sentiment varsa +30, Yüksek skor +40
            sniper_score = sig['score'] * 0.4
            if sq_res['is_firing']: sniper_score += 30
            elif sq_res['is_squeezing']: sniper_score += 15
            
            if sent_score > 0.2: sniper_score += 30
            
            # R/R Kontrolü
            zones = calculate_best_zones(df)
            rr_ratio = sig.get('rr_ratio', 1.5)
            
            if rr_ratio < 1.8: sniper_score -= 20 # Riskli bölgeleri ele

            if sniper_score > 60:
                # Seviyeleri belirle
                entry = live_px
                target = live_px * 1.03 # %3 hedef (standart)
                if zones['resistances']:
                    target = zones['resistances'][0][1]
                
                stop = live_px * 0.985 # %1.5 stop
                if zones['supports']:
                    stop = max(stop, zones['supports'][0][1])

                return {
                    "ticker": sym,
                    "score": round(sniper_score, 1),
                    "price": live_px,
                    "entry": round(entry, 2),
                    "target": round(target, 2),
                    "stop": round(stop, 2),
                    "target_pct": round(((target/entry)-1)*100, 1),
                    "reason": f"{'Haber Destekli ' if sent_score > 0.2 else ''}{'Squeeze Patlaması ' if sq_res['is_firing'] else 'Sıkışma Var'}",
                    "news": news[0]['title'] if news else "Haber akışı sakin."
                }
        except:
            return None
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(analyze_for_sniper, sym) for sym in symbol_list[:100]] # BIST100 sınırlı
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                candidates.append(res)

    # En iyi 5'liyi döndür
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:5]
