# pyrefly: ignore [missing-import]
import yfinance as yf
import pandas as pd
import sqlite3
import logging
from typing import List
from datetime import datetime
# pyrefly: ignore [missing-import]
import numpy as np


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketDataPipeline:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with normalized schema (Data Storage Quality)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dim_stock (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fact_daily_price (
                date DATE,
                ticker TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (date, ticker),
                FOREIGN KEY (ticker) REFERENCES dim_stock (ticker)
            )
        ''')
        self.conn.commit()
        logging.info("Database schema initialized.")

    def extract_data(self, tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Extract data from yfinance API"""
        logging.info(f"Extracting data for {len(tickers)} tickers from {start_date} to {end_date}")
        all_data = []
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date)
                
                if hist.empty:
                    logging.warning(f"No data found for {ticker}")
                    continue
                    
                hist['ticker'] = ticker
                hist.reset_index(inplace=True)
                
           
                try:
                    info = stock.info
                    company_name = info.get('longName', ticker)
                    sector = info.get('sector', 'Unknown')
                except:
                    company_name = ticker
                    sector = 'Unknown'
                    
                self._upsert_dim_stock(ticker, company_name, sector)
                all_data.append(hist)
            except Exception as e:
                logging.error(f"Failed to fetch data for {ticker}: {e}")
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    def _upsert_dim_stock(self, ticker, name, sector):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO dim_stock (ticker, company_name, sector)
            VALUES (?, ?, ?)
        ''', (ticker, name, sector))
        self.conn.commit()

    def quality_control(self, df: pd.DataFrame) -> pd.DataFrame:
        """Data Quality Control: Handle missing values, check datatypes, remove outliers"""
        logging.info("Starting Data Quality Control...")
        
       
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        
        
        if 'date' in df.columns:
            
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None).dt.date
        

        missing_count = df.isnull().sum().sum()
        if missing_count > 0:
            logging.warning(f"Found {missing_count} missing values. Forward filling...")
          
            group = df.groupby('ticker')
            for col in df.columns:
                if col != 'ticker':
                    df[col] = group[col].transform(lambda x: x.ffill().bfill())
     
        df['volume'] = df['volume'].astype(int)
        
  
        invalid_volume_count = len(df[df['volume'] < 0])
        if invalid_volume_count > 0:
            logging.warning(f"Found {invalid_volume_count} rows with negative volume. Fixing...")
            df = df[df['volume'] >= 0]
            
        logging.info("Data Quality Control completed.")
        return df[['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']]

    def load_data(self, df: pd.DataFrame):
        """Load cleaned data into SQLite database"""
        logging.info("Loading data into SQLite...")
        try:
            df.to_sql('fact_daily_price', self.conn, if_exists='append', index=False)
            logging.info(f"Successfully loaded {len(df)} records into fact_daily_price.")
        except ValueError as e:
            logging.error(f"Schema error: {e}")
        except sqlite3.IntegrityError:
            logging.warning("Data already exists for some dates. Skipping duplicate entries.")
        except Exception as e:
            logging.error(f"Error loading data: {e}")

    def run_pipeline(self, tickers: List[str], start_date: str, end_date: str):
        raw_data = self.extract_data(tickers, start_date, end_date)
        if not raw_data.empty:
            clean_data = self.quality_control(raw_data)
            self.load_data(clean_data)
        else:
            logging.error("No data extracted. Pipeline halted.")
