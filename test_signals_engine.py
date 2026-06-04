import pandas as pd
import numpy as np

def fast_get_core_signal(df, rules):
    # Bu fonksiyon saniyenin binde biri hizinda son bar icin oylama yapar.
    last_idx = -1
    total_weight = 0
    buy_votes = 0
    sell_votes = 0
    
    # Halka arz dynamic fallback (200 gunden az ise)
    is_ipo = len(df) < 200
    
    for name, rule_func in rules.items():
        if is_ipo:
            # isimde 150, 200 gibi uzun vadeli ibareler varsa es gec
            if "200" in name or "150" in name or "100" in name:
                continue
            weight = 20 # Kisa vadelilerin agirligini artir (Fallback kurali)
        else:
            weight = 10
            
        sig = rule_func(df) # Pandas Series doner (vektor)
        last_sig = sig.iloc[-1] if isinstance(sig, pd.Series) else sig[-1]
        
        total_weight += weight
        if last_sig == 1:
            buy_votes += weight
        elif last_sig == -1:
            sell_votes += weight
            
    if total_weight == 0:
        return {"decision": "Nötr", "score": 50}
        
    buy_pct = (buy_votes / total_weight) * 100
    sell_pct = (sell_votes / total_weight) * 100
    
    if buy_pct >= 60:
        dec = "Güçlü Al"
    elif buy_pct >= 50:
        dec = "Al"
    elif sell_pct >= 60:
        dec = "Güçlü Sat"
    elif sell_pct >= 50:
        dec = "Sat"
    else:
        dec = "Nötr"
        
    return {"decision": dec, "buy_pct": buy_pct, "sell_pct": sell_pct, "score": buy_pct}

