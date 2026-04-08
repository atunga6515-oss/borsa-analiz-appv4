import pandas as pd
import streamlit as st
import sqlite3
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_loader import fetch_data, get_live_price
from indicators import calculate_indicators, generate_signals_and_score
from patterns import detect_candlestick_patterns
from support_resistance import calculate_best_zones

# ============================================================
# BIST HİSSE LİSTELERİ
# ============================================================

BIST30_SYMBOLS = [
    "AKBNK", "ALARK", "ARCLK", "ASELS", "ASTOR", "BIMAS", "EKGYO", "ENKAI",
    "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS", "ISCTR", "KCHOL", "KONTR",
    "KOZAA", "KOZAL", "KRDMD", "ODAS", "OYAKC", "PETKM", "PGSUS", "SAHOL",
    "SASA", "SISE", "TCELL", "THYAO", "TOASO", "TUPRS", "YKBNK"
]

BIST100_SYMBOLS = BIST30_SYMBOLS + [
    "AEFES", "AFYON", "AGESA", "AHGAZ", "AKCNS", "AKFGY", "AKSA", "AKSEN",
    "AKYHO", "ALGYO", "ALTNY", "ALYAG", "ANSGR", "AGHOL", "AYDEM", "BASGZ",
    "BIENY", "BINHO", "BRISA", "BRYAT", "BTCIM", "BUCIM", "CANTE", "CCOLA",
    "CEMTS", "CIMSA", "CWENE", "DOAS", "DOHOL", "EGEEN", "ENJSA", "ESEN",
    "EUPWR", "GENIL", "GLYHO", "GOLTS", "GOZDE", "GRSEL", "GSDHO", "GESAN",
    "HALKB", "HUNER", "ISGYO", "ISMEN", "KAYSE", "KERVT", "KLSER", "KMPUR",
    "KORDS", "KOZAA", "LMKDC", "LOGO", "MAVI", "MGROS", "MIATK", "NETAS",
    "OTKAR", "PAPIL", "PATEK", "PEKGY", "QUAGR", "RGYAS", "RUBNS", "SARKY",
    "SELEC", "SKBNK", "SMRTG", "SOKM", "TAVHL", "TKFEN", "TKNSA", "TMSN",
    "TRGYO", "TURSG", "ULKER", "VAKBN", "VESBE", "VESTL", "YEOTK", "ZOREN"
]

BIST_ALL_SYMBOLS = list(set(BIST100_SYMBOLS + [
    "ACSEL", "ADEL", "ADESE", "ADGYO", "AEFES", "AFYON", "AGESA", "AGHOL",
    "AHGAZ", "AHSGY", "AKCNS", "AKFGY", "AKFYE", "AKGRT", "AKMGY", "AKSA",
    "AKSEN", "AKSGY", "AKSUE", "AKYHO", "ALCTL", "ALGYO", "ALKA", "ALKIM",
    "ALMAD", "ALTNY", "ALYAG", "ANELE", "ANGEN", "ANHYT", "ANSGR", "ARASE",
    "ARCLK", "ARDYZ", "ARENA", "ARSAN", "ARTMS", "ARZUM", "ATAGY", "ATAKP",
    "ATATP", "AVHOL", "AVOD", "AVPGY", "AVTUR", "AYCES", "AYDEM", "AYEN",
    "AYES", "AYGAZ", "AZTEK", "BAGFS", "BAKAB", "BALAT", "BANVT", "BARMA",
    "BASCM", "BASGZ", "BAYRK", "BERA", "BEYAZ", "BIENY", "BIGCH", "BIMAS",
    "BINHO", "BIOEN", "BIZIM", "BLCYT", "BMSCH", "BMSTL", "BNTAS", "BOBET",
    "BORLS", "BORSK", "BOSSA", "BRISA", "BRKSN", "BRKVY", "BRLSM", "BRMEN",
    "BRSAN", "BRYAT", "BSOKE", "BTCIM", "BUCIM", "BURCE", "BURVA", "CANTE",
    "CASA", "CCOLA", "CELHA", "CEMTS", "CEOEM", "CFRSA", "CGSGY", "CIMSA",
    "CINFO", "CLEBI", "CMBTN", "CONSE", "COSMO", "CRDFA", "CRFSA", "CUSAN",
    "CVKMD", "CWENE", "DAGHL", "DAGI", "DAPGM", "DARDL", "DENGE", "DERHL",
    "DERIM", "DESA", "DESPC", "DEVA", "DGATE", "DGNMO", "DIRIT", "DITAS",
    "DMRGD", "DMSAS", "DNISI", "DOAS", "DOBUR", "DOCO", "DOGUB", "DOHOL",
    "DOKTA", "DURDO", "DYOBY", "DZGYO", "EBEBK", "ECILC", "ECZYT", "EDIP",
    "EFORC", "EGEEN", "EGEPO", "EGGUB", "EGPRO", "EGSER", "EKGYO", "EKIZ",
    "EKOS", "EKSUN", "ELITE", "EMKEL", "EMNIS", "ENERY", "ENJSA", "ENKAI",
    "ENSRI", "EPLAS", "ERBOS", "EREGL", "ERSU", "ESEN", "ETILR", "EUPWR",
    "EUREN", "EUYO", "EYGYO", "FADE", "FENER", "FLAP", "FONET", "FORMT",
    "FORTE", "FRIGO", "FROTO", "FZLGY", "GARAN", "GARFA", "GEDIK", "GEDZA",
    "GENIL", "GENTS", "GEREL", "GESAN", "GIPTS", "GLBMD", "GLCVY", "GLYHO",
    "GMTAS", "GOKNR", "GOLTS", "GOODY", "GOZDE", "GRSEL", "GRTRK", "GSDDE",
    "GSDHO", "GSRAY", "GUBRF", "GWIND", "GZNMI", "HALKB", "HATEK", "HDFGS",
    "HEDEF", "HEKTS", "HKTM", "HLGYO", "HTTBT", "HUBVC", "HUNER", "HURGZ",
    "ICBCT", "ICUGS", "IDEAS", "IEYHO", "IHEVA", "IHGZT", "IHLAS", "IHLGM",
    "IHYAY", "IMASM", "INDES", "INFO", "INGRM", "INTEM", "INVEO", "INVES",
    "IPEKE", "ISBIR", "ISBTR", "ISCTR", "ISDMR", "ISFIN", "ISGSY", "ISGYO",
    "ISKPL", "ISKUR", "ISMEN", "ISSEN", "ITTFH", "IZFAS", "IZINV", "IZMDC",
    "JANTS", "KAPLM", "KAREL", "KARSN", "KARTN", "KARYE", "KATMR", "KAYSE",
    "KCHOL", "KENT", "KERVT", "KFEIN", "KGYO", "KIMMR", "KLGYO", "KLMSN",
    "KLNMA", "KLRHO", "KLSER", "KLSYN", "KMPUR", "KNFRT", "KONKA", "KONTR",
    "KONYA", "KORDS", "KOZAA", "KOZAL", "KRDMA", "KRDMB", "KRDMD", "KRGYO",
    "KRONT", "KRPLS", "KRSTL", "KRTEK", "KRVGD", "KTLEV", "KTSKR", "KUNDL",
    "KUVVA", "KUYAS", "KZBGY", "KZGYO", "LIDER", "LIDFA", "LILAK", "LINK",
    "LKMNH", "LMKDC", "LOGO", "LUKSK", "MAALT", "MACKO", "MAKIM", "MANAS",
    "MARBL", "MARKA", "MARTI", "MAVI", "MEDTR", "MEGAP", "MEKAG", "MERCN",
    "MERIT", "MERKO", "METRO", "METUR", "MGROS", "MHRGY", "MIATK", "MNDRS",
    "MNDTR", "MOBTL", "MOGAN", "MPARK", "MRDIN", "MRGYO", "MRSHL", "MSGYO",
    "MTRKS", "MTRYO", "MZHLD", "NATEN", "NETAS", "NIBAS", "NTGAZ", "NTHOL",
    "NUGYO", "NUHCM", "OBAMS", "ODAS", "OFSYM", "ONCSM", "ORCAY", "ORGE",
    "ORSBU", "OSTIM", "OTKAR", "OTTO", "OYAKC", "OYLUM", "OYYAT", "OZGYO",
    "OZKGY", "PAMEL", "PAPIL", "PARSN", "PASEU", "PATEK", "PCILT", "PEKGY",
    "PENGD", "PENTA", "PETKM", "PETUN", "PGSUS", "PINSU", "PKART", "PKENT",
    "PLTUR", "PNLSN", "PNSUT", "POLHO", "POLTK", "PRDGS", "PRKAB", "PRKME",
    "PRZMA", "PSDTC", "QUAGR", "RALYH", "RAYSG", "REEDR", "RGYAS", "RODRG",
    "RTALB", "RUBNS", "RYGYO", "RYSAS", "SAFKR", "SAHOL", "SAMAT", "SANEL",
    "SANFM", "SANKO", "SARKY", "SASA", "SAYAS", "SDTTR", "SEGYO", "SEKFK",
    "SEKUR", "SELEC", "SELGD", "SELVA", "SENVP", "SERVE", "SILVR", "SISE",
    "SKBNK", "SKYLP", "SMART", "SMRTG", "SNGYO", "SNICA", "SOKM", "SONME",
    "SRVGY", "SUNTK", "SUWEN", "TABGD", "TARKM", "TATGD", "TAVHL", "TCELL",
    "TEZOL", "THYAO", "TKFEN", "TKNSA", "TLMAN", "TMSN", "TOASO", "TRCAS",
    "TRGYO", "TRILC", "TSGYO", "TSKB", "TTKOM", "TTRAK", "TUKAS", "TUPRS",
    "TUREX", "TURSG", "ULKER", "ULUFA", "ULUSE", "ULUUN", "UMPAS", "UNLU",
    "USAK", "UZERB", "VAKBN", "VAKFN", "VAKKO", "VBTYZ", "VERTU", "VESBE",
    "VESTL", "VKFYO", "VKGYO", "VRGYO", "YAPRK", "YATAS", "YEOTK", "YESIL",
    "YGYO", "YKBNK", "YKSLN", "YUNSA", "YYLGD", "ZEDUR", "ZOREN", "ZRGYO"
]))

# ============================================================
# SEKTÖR HARİTASI (YENİ - Özellik 1)
# ============================================================

SECTOR_MAP = {
    "Bankacılık": ["AKBNK", "GARAN", "HALKB", "ISCTR", "VAKBN", "YKBNK", "SKBNK", "TSKB", "KLNMA"],
    "Holding": ["KCHOL", "SAHOL", "DOHOL", "GSDHO", "AGHOL", "GLYHO", "NTHOL", "INVEO"],
    "Enerji": ["AKSEN", "AYDEM", "ENJSA", "EUPWR", "CWENE", "ENKAI", "AYEN", "ZOREN", "ODAS"],
    "Havacılık & Ulaşım": ["THYAO", "PGSUS", "TAVHL", "CLEBI", "FROTO", "TOASO", "DOAS", "OTKAR"],
    "Demir-Çelik & Maden": ["EREGL", "KRDMD", "KOZAL", "KOZAA", "ISDMR", "CEMTS", "BRSAN"],
    "Perakende & Gıda": ["BIMAS", "SOKM", "MGROS", "ULKER", "CCOLA", "BANVT", "PNSUT", "TATGD"],
    "Teknoloji": ["ASELS", "LOGO", "NETAS", "ARENA", "INDES", "KRONT", "DGATE", "FONET", "PAPIL"],
    "İnşaat & GYO": ["EKGYO", "TRGYO", "ISGYO", "ALGYO", "KGYO", "SNGYO", "ENKAI"],
    "Kimya & Petrokimya": ["PETKM", "TUPRS", "SASA", "GUBRF", "HEKTS", "BAGFS", "ALKIM"],
    "Cam & Seramik": ["SISE", "TRKCM", "CIMSA", "BTCIM", "BUCIM", "BSOKE", "NUHCM"],
    "Tekstil & Moda": ["MAVI", "VAKKO", "BRISA", "BOSSA", "YUNSA", "DESA", "YATAS"],
    "Sigorta": ["AGESA", "ANSGR", "TURSG", "AKGRT", "ANHYT"],
    "Telekomünikasyon": ["TCELL", "TTKOM"],
}

def get_sector(symbol: str) -> str:
    """Hissenin sektörünü döndürür."""
    for sector, symbols in SECTOR_MAP.items():
        if symbol in symbols:
            return sector
    return "Diğer"

def get_sector_list() -> list:
    """Tüm sektör isimlerini döndürür."""
    return ["Tümü"] + sorted(SECTOR_MAP.keys()) + ["Diğer"]

def filter_by_sector(symbol_list: list, sector: str) -> list:
    """Belirtilen sektöre göre hisse listesini filtreler."""
    if sector == "Tümü":
        return symbol_list
    if sector == "Diğer":
        all_mapped = set()
        for syms in SECTOR_MAP.values():
            all_mapped.update(syms)
        return [s for s in symbol_list if s not in all_mapped]
    return [s for s in symbol_list if s in SECTOR_MAP.get(sector, [])]


# ============================================================
# TARAMA GEÇMİŞİ - SQLite (YENİ - Özellik 2)
# ============================================================

SCAN_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.db")

def _get_scan_conn():
    conn = sqlite3.connect(SCAN_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            scan_date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            score REAL,
            decision TEXT,
            price REAL,
            pct_change REAL
        )
    """)
    conn.commit()
    return conn

def save_scan_results(results_df: pd.DataFrame, username: str):
    """Tarama sonuçlarını SQLite'a kaydeder."""
    if results_df.empty:
        return
    conn = _get_scan_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    # Bugünün eski kayıtlarını sil (her taramada güncelle)
    conn.execute("DELETE FROM scan_history WHERE scan_date=? AND username=?", (today, username))
    for _, row in results_df.iterrows():
        conn.execute(
            "INSERT INTO scan_history (username, scan_date, ticker, score, decision, price, pct_change) VALUES (?,?,?,?,?,?,?)",
            (username, today, row.get('Hisse',''), row.get('Güven Skoru',0), row.get('Karar',''), 
             row.get('Fiyat (₺)',0), row.get('Değişim (%)',0))
        )
    conn.commit()
    conn.close()

def get_scan_history(username: str, days_back: int = 7) -> pd.DataFrame:
    """Belirli kullanıcıya ait son N günlük tarama geçmişini döndürür."""
    conn = _get_scan_conn()
    df = pd.read_sql_query(
        "SELECT * FROM scan_history WHERE username=? ORDER BY scan_date DESC, score DESC",
        conn, params=(username,)
    )
    conn.close()
    return df

def get_persistent_signals(username: str, min_days: int = 2) -> pd.DataFrame:
    """Kullanıcıya özel ardışık günlerde aynı yönde sinyal veren hisseleri bulur."""
    conn = _get_scan_conn()
    df = pd.read_sql_query(
        """SELECT ticker, decision, COUNT(DISTINCT scan_date) as gun_sayisi, 
           ROUND(AVG(score),1) as ort_skor,
           MIN(scan_date) as ilk_tarih, MAX(scan_date) as son_tarih
           FROM scan_history
           WHERE decision IN ('Al', 'Güçlü Al', 'Sat', 'Güçlü Sat') AND username=?
           GROUP BY ticker, decision
           HAVING COUNT(DISTINCT scan_date) >= ?
           ORDER BY gun_sayisi DESC, ort_skor DESC""",
        conn, params=(username, min_days)
    )
    conn.close()
    return df


# ============================================================
# WATCHLIST - İzleme Listesi (YENİ - Özellik 8)
# ============================================================

def _get_watchlist_conn():
    conn = sqlite3.connect(SCAN_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ticker TEXT NOT NULL,
            added_date TEXT NOT NULL,
            note TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn

def add_to_watchlist(username: str, ticker: str, note: str = ""):
    conn = _get_watchlist_conn()
    try:
        # User bazlı unique kontrolü için INSERT OR IGNORE yerine elle kontrol veya farklı şema gerekebilir.
        # Basitlik için username+ticker bazlı siliyoruz önce (varsa güncelleme gibi).
        conn.execute("DELETE FROM watchlist WHERE username=? AND ticker=?", (username, ticker))
        conn.execute("INSERT INTO watchlist (username, ticker, added_date, note) VALUES (?,?,?,?)",
                      (username, ticker, datetime.now().strftime("%Y-%m-%d %H:%M"), note))
        conn.commit()
    except Exception:
        pass
    conn.close()

def remove_from_watchlist(username: str, ticker: str):
    conn = _get_watchlist_conn()
    conn.execute("DELETE FROM watchlist WHERE username=? AND ticker=?", (username, ticker))
    conn.commit()
    conn.close()

def get_watchlist(username: str) -> pd.DataFrame:
    conn = _get_watchlist_conn()
    df = pd.read_sql_query("SELECT * FROM watchlist WHERE username=? ORDER BY added_date DESC", conn, params=(username,))
    conn.close()
    return df


# ============================================================
# TEKİL HİSSE ANALİZ FONKSİYONU (Paralel tarama için)
# ============================================================

def _analyze_single_stock(sym: str) -> dict:
    """Tek bir hisseyi analiz eder ve sonuç sözlüğü döndürür. ThreadPool için."""
    try:
        df = fetch_data(sym, interval="1d", period="6mo")
        if df.empty or len(df) < 50:
            return None
            
        df = calculate_indicators(df)
        sig = generate_signals_and_score(df)
        
        # Canlı Fiyat & Değişim
        live_px = get_live_price(sym)
        if live_px > 0 and len(df) >= 2:
            prev_close = df['Close'].iloc[-2]
            pct_change = ((live_px - prev_close) / prev_close) * 100
            display_price = live_px
        else:
            display_price = df['Close'].iloc[-1]
            pct_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100 if len(df)>=2 else 0

        # Hacim Patlaması
        vol_breakout = "-"
        if len(df) >= 11:
            avg_vol = df['Volume'].iloc[-11:-1].mean()
            today_vol = df['Volume'].iloc[-1]
            if today_vol > avg_vol * 1.5 and df['Close'].iloc[-1] > df['Open'].iloc[-1]:
                vol_breakout = "🚀 Hacim Şoku"

        # Formasyon
        pattern_text = "-"
        p_res = detect_candlestick_patterns(df)
        if p_res and p_res.get('summary') and "tespit edilmedi" not in p_res.get('summary'):
            pattern_text = p_res['summary'].splitlines()[0].replace('*', '').replace('Tespit edildi: ', '').strip()

        # Dipten Dönüş
        reversal = "-"
        if len(df) >= 3 and 'RSI_14' in df.columns:
            rsi_today = df['RSI_14'].iloc[-1]
            rsi_yest = df['RSI_14'].iloc[-2]
            if pd.notna(rsi_today) and pd.notna(rsi_yest):
                if rsi_yest < 35 and rsi_today > rsi_yest and rsi_today > 30:
                    reversal = "🔥 Dipten Dönüş"

        # Destek/Direnç
        zones = calculate_best_zones(df)
        dist_sup = "-"
        dist_res = "-"
        if zones.get('supports'):
            sup = zones['supports'][0]['price']
            d_pct = ((display_price - sup) / display_price) * 100
            dist_sup = f"%{d_pct:.1f}" if d_pct > 0 else "Destekte"
        if zones.get('resistances'):
            res_price = zones['resistances'][0]['price']
            r_pct = ((res_price - display_price) / display_price) * 100
            dist_res = f"%{r_pct:.1f}" if r_pct > 0 else "Dirençte"

        # 1H Uyum
        df_1h = fetch_data(sym, interval="1h", period="1mo")
        trend_uyum = "Tekil"
        if not df_1h.empty and len(df_1h) >= 20:
            df_1h = calculate_indicators(df_1h)
            sig_1h = generate_signals_and_score(df_1h)
            if sig['decision'] in ["Al", "Güçlü Al"] and sig_1h['decision'] in ["Al", "Güçlü Al"]:
                trend_uyum = "✅ Çift AL (1D+1H)"
            elif sig['decision'] in ["Sat", "Güçlü Sat"] and sig_1h['decision'] in ["Sat", "Güçlü Sat"]:
                trend_uyum = "❌ Çift SAT (1D+1H)"
            else:
                trend_uyum = "⚠️ Karışık"

        rsi_val = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else None
        sector = get_sector(sym)

        return {
            "Hisse": sym,
            "Sektör": sector,
            "Fiyat (₺)": round(display_price, 2),
            "Değişim (%)": round(pct_change, 2),
            "Güven Skoru": sig['score'],
            "Karar": sig['decision'],
            "1D+1H Uyum": trend_uyum,
            "Hacim Patlaması": vol_breakout,
            "Dipten Dönüş": reversal,
            "Mum Formasyonu": pattern_text,
            "RSI": round(rsi_val, 1) if rsi_val and pd.notna(rsi_val) else "-",
            "Desteğe Uzaklık": dist_sup,
            "Dirence Uzaklık": dist_res
        }
    except Exception:
        return None


# ============================================================
# ANA TARAYICI FONKSİYONU (Paralel + Sektör + Geçmiş Kayıt)
# ============================================================

def run_screener(symbol_list: list, username: str, progress_bar=None, max_workers: int = 5) -> pd.DataFrame:
    """
    Paralel çoklu iş parçacığı ile hisseleri tarar.
    Sonuçları otomatik olarak SQLite'a kaydeder.
    """
    results = []
    total = len(symbol_list)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sym = {executor.submit(_analyze_single_stock, sym): sym for sym in symbol_list}
        
        for future in as_completed(future_to_sym):
            completed += 1
            sym = future_to_sym[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception:
                pass
            
            if progress_bar:
                progress_bar.progress(completed / total, text=f"{sym} tarandı ({completed}/{total})")
            
    if not results:
        return pd.DataFrame()
        
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by="Güven Skoru", ascending=False).reset_index(drop=True)
    
    # Tarama sonuçlarını SQLite'a kaydet (Özellik 2)
    save_scan_results(res_df, username)
    
    return res_df
