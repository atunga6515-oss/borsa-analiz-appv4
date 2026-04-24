import json
from morning_sniper import get_morning_sniper_candidates
from indicators import generate_signals_and_score
from data_loader import fetch_data
import warnings
warnings.filterwarnings('ignore')

print("📌 YUNSA: TAKAS VE SNIPER MOTORU TESTİ")
print("-" * 50)

# 1. Takas Motoru Entegreli PGS Puanı Testi
df = fetch_data("YUNSA", "1d", "6mo")
if not df.empty:
    sig = generate_signals_and_score(df, ticker="YUNSA")
    print("\n🧐 INDICATORS / PGS (Takas Motoru) SONUCU:")
    print(f"👉 Karar: {sig.get('decision')}")
    print(f"👉 Güven Seviyesi: {sig.get('conviction_level')}")
    print(f"👉 PGS Skoru: {sig.get('pgs')} / 100")
    print(f"👉 Özet Uyarılar: | {' | '.join(sig.get('summary', []))} |")
else:
    print("Veri çekilemedi.")

# 2. Morning Sniper (Geopolitik ve Dinamik Stop Testi)
print("\n" + "-" * 50)
print("🎯 MORNING SNIPER (GEO-BOOST & DİNAMİK R/R) SONUCU:")
candidates = get_morning_sniper_candidates(["YUNSA", "THYAO"]) # THYAO ile karşılaştırma
for c in candidates:
    print(f"\n[{c['ticker']}]")
    print(f"Puan: {c['score']}")
    print(f"Nedenler: {c['reason']}")
    print(f"Giriş: {c['entry']} | Hedef: {c['target']} (+%{c['target_pct']}) | Stop: {c['stop']}")
    
print("\n✅ Test Tamamlandı.")
