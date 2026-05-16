import sqlite3
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
import logging

class MarketAnalytics:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        
    def get_portfolio_data(self) -> pd.DataFrame:
        """Fetch joined data using SQL"""
        query = '''
            SELECT f.date, f.ticker, d.company_name, d.sector, 
                   f.open, f.high, f.low, f.close, f.volume
            FROM fact_daily_price f
            JOIN dim_stock d ON f.ticker = d.ticker
            ORDER BY f.date ASC
        '''
        try:
            df = pd.read_sql(query, self.conn)
            df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            logging.error(f"Failed to fetch portfolio data: {e}")
            return pd.DataFrame()

    def calculate_daily_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
            
       
        pivot_df = df.pivot(index='date', columns='ticker', values='close')
        returns = pivot_df.pct_change().dropna()
        return returns

    def calculate_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Volatility, Annualized Return, Sharpe Ratio"""
        returns = self.calculate_daily_returns(df)
        if returns.empty:
            return pd.DataFrame()
        
        stats = []
        for col in returns.columns:
            annual_return = returns[col].mean() * 252
            annual_volatility = returns[col].std() * np.sqrt(252)
            
    
            rf_rate = 0.02
            sharpe_ratio = (annual_return - rf_rate) / annual_volatility if annual_volatility != 0 else 0
            

            var_95 = np.percentile(returns[col], 5)
            

            cumulative_returns = (1 + returns[col]).cumprod()
            rolling_max = cumulative_returns.cummax()
            drawdowns = cumulative_returns / rolling_max - 1
            max_drawdown = drawdowns.min()
            
            stats.append({
                'Ticker': col,
                'Annualized Return': annual_return,
                'Annualized Volatility': annual_volatility,
                'Sharpe Ratio': sharpe_ratio,
                'VaR (95%)': var_95,
                'Max Drawdown': max_drawdown
            })
            
        return pd.DataFrame(stats)

    def monte_carlo_simulation(self, df: pd.DataFrame, ticker: str, days: int = 30, simulations: int = 100) -> pd.DataFrame:
        """Predictive Analytics: Monte Carlo Simulation"""
        returns = self.calculate_daily_returns(df)
        if ticker not in returns.columns:
            raise ValueError(f"Ticker {ticker} not found in data.")
            
        mu = returns[ticker].mean()
        sigma = returns[ticker].std()
        
        last_price = df[df['ticker'] == ticker]['close'].iloc[-1]
        
        simulation_df = pd.DataFrame()
        for x in range(simulations):
            price_series = [last_price]
            for y in range(days):
  
                shock = mu + sigma * np.random.normal()
                price = price_series[-1] * (1 + shock)
                price_series.append(price)
            simulation_df[f'Sim_{x}'] = price_series
            
        return simulation_df
