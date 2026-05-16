import pandas as pd
import logging
import os
from src.analytics import MarketAnalytics

class ExcelReportGenerator:
    def __init__(self, analytics: MarketAnalytics):
        self.analytics = analytics

    def generate_report(self, output_path: str):
        logging.info("Generating Excel Report...")
        df = self.analytics.get_portfolio_data()
        
        if df.empty:
            logging.error("No data available to generate report.")
            return
            
        returns = self.analytics.calculate_daily_returns(df)
        stats = self.analytics.calculate_statistics(df)
        correlation = returns.corr()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
       
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                stats.to_excel(writer, sheet_name='Portfolio Summary', index=False)
                correlation.to_excel(writer, sheet_name='Correlation Matrix')
                
                
                df.tail(1000).to_excel(writer, sheet_name='Raw Data', index=False)
                
                
                workbook = writer.book
                worksheet = writer.sheets['Portfolio Summary']
                
                
                for col in worksheet.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column].width = adjusted_width
                    
            logging.info(f"Report successfully saved to {output_path}")
        except Exception as e:
            logging.error(f"Failed to generate Excel report: {e}")
