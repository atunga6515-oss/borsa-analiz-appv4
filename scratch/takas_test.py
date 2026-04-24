import isyatirimhisse as isy
from datetime import datetime, timedelta

prev = (datetime.now() - timedelta(days=5)).strftime('%d-%m-%Y')
today = datetime.now().strftime('%d-%m-%Y')

try:
    data = isy.fetch_stock_data(symbol='THYAO', start_date=prev, end_date=today)
    print("KEYS:", data.keys() if hasattr(data, 'keys') else 'No keys')
    print(data.head())
    print("COLUMNS:", data.columns.tolist() if hasattr(data, 'columns') else '')
except Exception as e:
    print(e)
