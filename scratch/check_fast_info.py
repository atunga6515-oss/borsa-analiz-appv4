import yfinance as yf
import json

def compare_methods(symbol):
    print(f"--- {symbol} ---")
    tkr = f"{symbol}.IS"
    t = yf.Ticker(tkr)
    
    # Method 1: info
    info = t.info
    info_data = {
        "pe": info.get("trailingPE"),
        "pb": info.get("priceToBook"),
        "eps": info.get("trailingEps"),
        "bv": info.get("bookValue"),
        "price": info.get("currentPrice")
    }
    
    # Method 2: fast_info (new in yfinance)
    try:
        fi = t.fast_info
        fi_data = {
            "last_price": getattr(fi, 'last_price', None),
            "market_cap": getattr(fi, 'market_cap', None),
            "book_value": getattr(fi, 'book_value', None) # Note: fast_info might have different names
        }
        # To see all attributes of fast_info:
        # fi_all = {k: getattr(fi, k) for k in dir(fi) if not k.startswith('_')}
    except Exception as e:
        fi_data = {"error": str(e)}

    print("Info Data:", json.dumps(info_data, indent=2))
    print("Fast Info Data:", json.dumps(fi_data, indent=2))

if __name__ == "__main__":
    compare_methods("MERIT")
    compare_methods("THYAO")
