import yfinance as yf
import json

def test_ticker_info(symbol):
    print(f"Testing ticker: {symbol}")
    tkr = f"{symbol}.IS"
    ticker = yf.Ticker(tkr)
    # yfinance cache'i bozmak için bazen info yerine fast_info veya diğer metodlar denenebilir
    info = ticker.info
    print(json.dumps({k: info.get(k) for k in ["trailingPE", "forwardPE", "priceToBook", "trailingEps", "bookValue", "dividendYield"]}, indent=2))

if __name__ == "__main__":
    test_ticker_info("MERIT")
    test_ticker_info("THYAO")
