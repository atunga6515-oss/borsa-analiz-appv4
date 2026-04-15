import sys
import os
import pandas as pd
import streamlit as st

# Mock streamlit secrets if needed
if not hasattr(st, "secrets"):
    st.secrets = {}

# Import our module
sys.path.append(os.getcwd())
try:
    from data_loader import _download_from_yfinance, _make_ticker
    
    ticker = _make_ticker("THYAO")
    print(f"Testing ticker: {ticker}")
    df = _download_from_yfinance(ticker, "1d", period="5d")
    print(f"Result empty: {df.empty}")
    if not df.empty:
        print(f"Columns: {df.columns}")
        print(df.tail(2))
except Exception as e:
    print(f"Error: {e}")
