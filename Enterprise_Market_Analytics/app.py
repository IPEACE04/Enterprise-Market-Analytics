import sys
import os


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px
# pyrefly: ignore [missing-import]
import plotly.graph_objects as go
from src.analytics import MarketAnalytics

st.set_page_config(page_title="Enterprise Equity Analytics", layout="wide", page_icon="")

st.title("Enterprise Equity Analytics Dashboard")
st.markdown("""
This dashboard showcases a full-stack Data Analytics pipeline designed for production scale:
**Data Extraction (yfinance)  Quality Control , SQL Data Warehouse , Analytics Engine , Interactive UI**
""")

db_path = "data/market_warehouse.db"

@st.cache_data
def load_data():
    if not os.path.exists(db_path):
        return None, None, None
    analytics = MarketAnalytics(db_path)
    df = analytics.get_portfolio_data()
    if df.empty:
        return None, None, None
        
    stats = analytics.calculate_statistics(df)
    returns = analytics.calculate_daily_returns(df)
    return df, stats, returns

df, stats, returns = load_data()
analytics = MarketAnalytics(db_path)

if df is None:
    st.warning("No data found. Please run `python main.py` in the terminal first to build the database")
    st.stop()
    

st.header("Portfolio Overview & Risk Metrics")
kpi_cols = st.columns(len(stats))
for i, row in stats.iterrows():
    with kpi_cols[i]:
        st.metric(
            label=f"{row['Ticker']} Annual Return", 
            value=f"{row['Annualized Return']:.2%}",
            delta=f"Sharpe: {row['Sharpe Ratio']:.2f}"
        )
        
st.markdown("""
<div style="font-size: 0.8em; color: gray;">
* <b>Annual Return</b>: Expected yearly return based on historical data.<br>
* <b>Sharpe Ratio</b>: Risk-adjusted return. >1 is good, >2 is very good.
</div>
""", unsafe_allow_html=True)


st.header("Technical Analysis & Price Action")
tickers = df['ticker'].unique()
selected_ticker = st.selectbox("Select Asset for Deep Dive", tickers)

asset_data = df[df['ticker'] == selected_ticker].copy()
asset_data['SMA_20'] = asset_data['close'].rolling(window=20).mean()
asset_data['SMA_50'] = asset_data['close'].rolling(window=50).mean()

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=asset_data['date'],
    open=asset_data['open'],
    high=asset_data['high'],
    low=asset_data['low'],
    close=asset_data['close'],
    name='Price Action'
))
fig.add_trace(go.Scatter(x=asset_data['date'], y=asset_data['SMA_20'], name='20-Day SMA', line=dict(dash='dot', color='orange')))
fig.add_trace(go.Scatter(x=asset_data['date'], y=asset_data['SMA_50'], name='50-Day SMA', line=dict(dash='dash', color='blue')))
fig.update_layout(title=f"{selected_ticker} Technical Analysis", height=600, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, width='stretch')


st.header("Predictive Analytics: Monte Carlo Simulation")
st.markdown(f"Simulating 100 possible future price paths for **{selected_ticker}** over the next 30 trading days based on historical volatility and drift.")

col1, col2 = st.columns([1, 4])
with col1:
    sim_days = st.slider("Simulation Days", min_value=10, max_value=90, value=30, step=10)
    run_sim = st.button("Run Simulation", type="primary")

with col2:
    if run_sim:
        with st.spinner(f'Running 100 simulations for {selected_ticker}...'):
            sim_df = analytics.monte_carlo_simulation(df, selected_ticker, days=sim_days)
            
            fig_sim = go.Figure()
            for col in sim_df.columns:
                fig_sim.add_trace(go.Scatter(y=sim_df[col], mode='lines', line=dict(width=1, color='rgba(0, 100, 255, 0.1)'), showlegend=False))
            
           
            fig_sim.add_trace(go.Scatter(y=sim_df.mean(axis=1), mode='lines', line=dict(width=3, color='red'), name='Expected Path (Mean)'))
            
            fig_sim.update_layout(title=f"{selected_ticker} Future Price Paths ({sim_days} Days)", xaxis_title="Days Ahead", yaxis_title="Predicted Price ($)", height=500)
            st.plotly_chart(fig_sim, width='stretch')


st.header("Asset Correlation Matrix")
st.markdown("Understanding how assets move in relation to each other is crucial for portfolio diversification.")
corr = returns.corr()
fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale='RdBu_r', aspect="auto")
st.plotly_chart(fig_corr, width='stretch')


st.header("Data Quality & Storage Explorer (SQLite)")
st.dataframe(df.tail(100), use_container_width=True)
