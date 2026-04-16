import yfinance as yf
import math
import json

def get_fundamental_data_test(ticker_symbol: str) -> dict:
    try:
        tkr = ticker_symbol if ticker_symbol.endswith(".IS") else f"{ticker_symbol}.IS"
        ticker = yf.Ticker(tkr)
        info = ticker.info
        
        pe = info.get("trailingPE") or info.get("forwardPE") or 0
        pb = info.get("priceToBook") or 0
        eps = info.get("trailingEps") or info.get("forwardEps") or info.get("epsTrailingTwelveMonths") or 0
        bv = info.get("bookValue") or 0
        div_yield = info.get("dividendYield") or 0
        curr_price = info.get("currentPrice") or info.get("previousClose") or 0
        
        if not bv and pb and curr_price:
            bv = curr_price / pb

        pe = float(pe) if pe is not None else 0.0
        pb = float(pb) if pb is not None else 0.0
        eps = float(eps) if eps is not None else 0.0
        bv = float(bv) if bv is not None else 0.0
        div_yield = float(div_yield) * 100 if div_yield is not None else 0.0
        
        graham_value = 0.0
        if eps > 0 and bv > 0:
            graham_value = math.sqrt(22.5 * eps * bv)
            
        return {
            "pe": round(pe, 2),
            "pb": round(pb, 2),
            "eps": round(eps, 2),
            "bv": round(bv, 2),
            "div_yield": round(div_yield, 2),
            "graham_value": round(graham_value, 2) if graham_value > 0 else "N/A"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print(json.dumps(get_fundamental_data_test("MERIT"), indent=2))
