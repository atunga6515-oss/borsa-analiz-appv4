import pandas as pd
from data_loader import fetch_data, get_live_price
from indicators import calculate_indicators, generate_signals_and_score, get_market_regime, check_volatility_squeeze
from kap_news import get_sentiment_summary
from support_resistance import calculate_best_zones
from screener import BIST100_SYMBOLS
from patterns import detect_candlestick_patterns
import concurrent.futures

# Jeopolitik Hedef Hisseler
GEO_TARGETS = ['TRCAS', 'AYCES', 'MERIT', 'YUNSA']
GEO_KEYWORDS = ['hürmüz', 'ateşkes', 'trump', 'petrol', 'liman', 'nükleer', 'anlaşma']

def get_morning_sniper_candidates(symbol_list=None):
    """
    Borsa açılışında patlama potansiyeli en yüksek 3-5 hisseyi bulur.
    2026 Jeopolitik Konjonktürüne göre güncellenmiştir (Chaos Engine, Geo-Boost, Super Sniper).
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
            
            # --- 1. Haber Analizi ve TRUMP FİLTRESİ (Chaos Engine) ---
            sent_score, news = get_sentiment_summary(sym)
            if sent_score < -0.5:
                # Trump Filtresi: Negatif şok (risk yüksekse eliyoruz)
                return None
                
            # --- 2. Sektörel ve Jeopolitik Boost (GEO-BOOST) ---
            geo_boost_pts = 0
            is_geo = False
            if sym in GEO_TARGETS and news:
                news_text = " ".join([n['title'] for n in news]).lower()
                if any(kw in news_text for kw in GEO_KEYWORDS):
                    geo_boost_pts = 20
                    is_geo = True
                    
            # --- 3. Açılış Gap Analizi & Süper Sniper ---
            # Dünkü kapanış vs Bugünkü fiyat (live) hesaplaması için df'in son birkaç gününe bakalım
            prev_close = df['Close'].iloc[-1]
            if len(df) >= 2:
                # Eğer live_px sondan df'teki değerle birebir aynıysa, muhtemelen son gün henüz piyasa açılmamıştır. -2'yi prev kabul edebiliriz.
                if abs((df['Close'].iloc[-1] - live_px) / live_px) < 0.001:
                    prev_close = df['Close'].iloc[-2]
            
            gap_pct = ((live_px / prev_close) - 1.0) * 100.0 if prev_close > 0 else 0.0
            
            # --- 4. Squeeze Analizi ---
            sq_res = check_volatility_squeeze(df)
            is_super_sniper = False
            if gap_pct > 1.5 and sq_res['is_firing']:
                is_super_sniper = True
                
            # --- 5. Genel Skor ve Pattern (Yutan Boğa Çarpanı) ---
            sig = generate_signals_and_score(df, ticker=sym, market_regime=market_regime, sentiment_score=sent_score)
            patterns_info = detect_candlestick_patterns(df)
            pattern_summary = patterns_info.get('summary', '')
            has_bullish_engulfing = 'Yutan Boğa' in pattern_summary or 'Bullish Engulfing' in pattern_summary
            
            # SNIPER PUANLAMA
            sniper_score = sig['score'] * 0.4
            if sq_res['is_firing']: sniper_score += 30
            elif sq_res['is_squeezing']: sniper_score += 15
            
            if sent_score > 0.2: sniper_score += 30
            
            sniper_score += geo_boost_pts  # GEO-BOOST
            
            # Formasyon çarpanı
            if has_bullish_engulfing:
                sniper_score *= 1.2
            
            # R/R Kontrolü
            rr_ratio = sig.get('rr_ratio', 1.5)
            if rr_ratio < 1.8 and not is_super_sniper: 
                sniper_score -= 20 # Riskli bölgeleri ele, ama süper sniper ise tolere et
                
            if sniper_score > 60 or is_super_sniper:
                # --- 6. Dinamik Stop/Hedef Revizyonu (Derinlik Analizi - Hacim TRY) ---
                df['Turnover'] = df['Close'] * df['Volume']
                avg_turnover = df['Turnover'].tail(20).mean()
                
                is_deep = avg_turnover >= 100_000_000  # 100 Milyon TRY sınır
                
                tp_pct = 1.03 if is_deep else 1.05
                sl_pct = 0.985 if is_deep else 0.975
                
                entry = live_px
                target = live_px * tp_pct
                stop = live_px * sl_pct
                
                zones = calculate_best_zones(df)
                if zones['resistances']:
                    target = max(target, zones['resistances'][0][1])
                if zones['supports']:
                    stop = max(stop, zones['supports'][0][1])

                reason_str = ""
                if is_super_sniper: reason_str += "[SÜPER SNIPER] (Gap+Squeeze) "
                if is_geo: reason_str += "[GEO-BOOST] "
                if has_bullish_engulfing: reason_str += "[Yutan Boğa] "
                if sent_score > 0.2: reason_str += "[Haber Destekli] "
                if sq_res['is_firing'] and not is_super_sniper: reason_str += "[Squeeze Patlaması] "
                if sq_res['is_squeezing'] and not sq_res['is_firing']: reason_str += "[Sıkışma Var] "
                
                if not reason_str: reason_str = "Teknik Sinyal"

                return {
                    "ticker": sym,
                    "score": round(sniper_score, 1),
                    "price": live_px,
                    "entry": round(entry, 2),
                    "target": round(target, 2),
                    "stop": round(stop, 2),
                    "target_pct": round(((target/entry)-1)*100, 1),
                    "reason": reason_str.strip(),
                    "news": news[0]['title'] if news else "Haber akışı sakin."
                }
        except:
            return None
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(analyze_for_sniper, sym) for sym in symbol_list] 
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                candidates.append(res)

    # En iyi 5'liyi döndür
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:5]
