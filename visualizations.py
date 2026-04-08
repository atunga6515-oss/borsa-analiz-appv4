import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def create_advanced_chart(df: pd.DataFrame, symbol: str, risk: dict = None, sr_data: dict = None) -> go.Figure:
    if df.empty:
        return go.Figure()

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])

    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name=f'{symbol}'),
                  row=1, col=1)

    if 'SMA_20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name='SMA 20'), row=1, col=1)
    if 'SMA_50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='blue', width=1), name='SMA 50'), row=1, col=1)

    if 'BBU_20_2.0' in df.columns and 'BBL_20_2.0' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], line=dict(color='rgba(200,200,200,0.3)', width=1, dash='dot'), name='BB Üst'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], line=dict(color='rgba(200,200,200,0.3)', width=1, dash='dot'), name='BB Alt'), row=1, col=1)

    if risk and 'SL' in risk:
        sl_value = risk['SL']
        tp1_value = risk['TP1']
        tp2_value = risk['TP2']
        fig.add_hline(y=sl_value, line_dash="dash", line_color="red", annotation_text="Stop-Loss", row=1, col=1)
        fig.add_hline(y=tp1_value, line_dash="dash", line_color="lightgreen", annotation_text="TP1", row=1, col=1)
        fig.add_hline(y=tp2_value, line_dash="dash", line_color="green", annotation_text="TP2", row=1, col=1)

    # Destek & Direnç çizgileri
    if sr_data:
        # Destek seviyeleri (yeşil kesikli çizgiler)
        for label, val in sr_data.get('best_buy_zones', []):
            fig.add_hline(y=val, line_dash="dot", line_color="lime", line_width=1,
                          annotation_text=f"🟢 {label}: {val}", annotation_position="bottom left",
                          row=1, col=1)
        # Direnç seviyeleri (turuncu kesikli çizgiler)
        for label, val in sr_data.get('best_sell_zones', []):
            fig.add_hline(y=val, line_dash="dot", line_color="orange", line_width=1,
                          annotation_text=f"🔴 {label}: {val}", annotation_position="top left",
                          row=1, col=1)

    if 'MACD' in df.columns and 'MACDs' in df.columns and 'MACDh' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='blue', width=1), name='MACD'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs'], line=dict(color='red', width=1), name='Signal'), row=2, col=1)
        colors = ['green' if val > 0 else 'red' for val in df['MACDh']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh'], marker_color=colors, name='MACD Hist'), row=2, col=1)

    if 'RSI_14' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], line=dict(color='purple', width=1.5), name='RSI 14'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

    fig.update_layout(title=f'{symbol} Gelişmiş Analiz', template='plotly_dark', height=800, margin=dict(l=20, r=20, t=50, b=20), xaxis_rangeslider_visible=False, showlegend=False)
    return fig

def create_ml_chart(df: pd.DataFrame, ml_data: dict, symbol: str) -> go.Figure:
    """Yapay Zeka (Scikit-Learn) tahmini için grafik çizici."""
    fig = go.Figure()
    
    # Geçmiş Gerçek Fiyat
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Gerçek Kapanış', line=dict(color='white', width=2)))
    
    # Geçmiş ML Fit (Eğrinin nasıl oturduğu)
    fig.add_trace(go.Scatter(x=df.index, y=ml_data['historical_fit'], name='ML Trend Fit', line=dict(color='orange', width=2, dash='dash')))
    
    # Gelecek Tahmini
    future_df = ml_data['future_df']
    
    # Hata Payı (Koni)
    fig.add_trace(go.Scatter(
        x=future_df.index.tolist() + future_df.index.tolist()[::-1],
        y=future_df['Üst Bant'].tolist() + future_df['Alt Bant'].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(0, 176, 246, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=True,
        name='Güven Aralığı'
    ))
    
    fig.add_trace(go.Scatter(x=future_df.index, y=future_df['Fiyat Tahmini'], name='Gelecek Projeksiyonu', line=dict(color='cyan', width=3)))

    fig.update_layout(title=f'{symbol} - Makine Öğrenmesi Fiyat Tahmini (30 Gün)', template='plotly_dark', height=600, hovermode="x unified")
    return fig

def create_equity_curve_chart(equity_df: pd.DataFrame, symbol: str) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x=equity_df.index, y=equity_df['Equity'], name='Portföy Değeri (TRY)', line=dict(color='green', width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=equity_df.index, y=equity_df['Drawdown']*100, name='Drawdown (%)', line=dict(color='red', width=1), fill='tozeroy', fillcolor='rgba(255,0,0,0.1)'), secondary_y=True)

    fig.update_layout(title=f'{symbol} Backtest Simülasyonu', template='plotly_dark', height=500)
    fig.update_yaxes(title_text="Toplam Kasa (TRY)", secondary_y=False)
    fig.update_yaxes(title_text="Kayıp Oranı (%)", secondary_y=True)
    return fig
