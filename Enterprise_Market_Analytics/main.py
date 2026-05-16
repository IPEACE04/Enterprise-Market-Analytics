import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.data_pipeline import MarketDataPipeline
from src.analytics import MarketAnalytics
from src.report_generator import ExcelReportGenerator
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    print("Starting Enterprise Equity Analytics Pipeline")
 
    db_dir = "data"
    reports_dir = "reports"
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    db_path = os.path.join(db_dir, "market_warehouse.db")
    
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "SPY"]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 3)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print("\n[1/4] Running Data Ingestion & Quality Control...")
    pipeline = MarketDataPipeline(db_path)
    pipeline.run_pipeline(tickers, start_date=start_date_str, end_date=end_date_str)
    
    print("\n[2/4] Executing Financial Analytics Engine...")
    analytics = MarketAnalytics(db_path)
    df = analytics.get_portfolio_data()
    if df.empty:
        print("Pipeline failed: No data available for analysis")
        return
        
    stats = analytics.calculate_statistics(df)
    print("\nPortfolio Statistics:")
    print(stats.to_string(index=False))
    
    print("\n[3/4] Generating Automated Excel Report...")
    report_gen = ExcelReportGenerator(analytics)
    report_path = os.path.join(reports_dir, "Portfolio_Analysis_Report.xlsx")
    report_gen.generate_report(report_path)
    
    print("\n[4/4] Pipeline Complete! ")
    print(f"Database updated: {db_path}")
    print(f"Report generated: {report_path}")
    print("\nRun 'streamlit run app.py' to view the interactive web dashboard.")

if __name__ == "__main__":
    main()
