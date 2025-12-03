import yfinance as yf
import pandas as pd
import os
from typing import Optional

class DataLoader:
    def __init__(self):
        pass

    def get_stock_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        :param ticker: 股票代码 (e.g., 'AAPL', '0700.HK')
        :param period: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        :param interval: 数据间隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        :return: DataFrame with columns [Open, High, Low, Close, Volume, etc.]
        """
        print(f"正在获取 {ticker} 的数据...")
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                print(f"警告: 未找到 {ticker} 的数据。")
                return None
            
            # 重置索引，让 Date 成为一列，方便后续处理
            df = df.reset_index()
            return df
        except Exception as e:
            print(f"获取 {ticker} 数据时出错: {e}")
            # Fallback to local data if API fails (for testing purposes)
            if os.path.exists("data/sample_data.csv"):
                print(f"切换到本地测试数据: data/sample_data.csv")
                df = pd.read_csv("data/sample_data.csv")
                return df
            return None

    def get_stock_info(self, ticker: str) -> dict:
        """
        获取股票基本信息
        """
        try:
            stock = yf.Ticker(ticker)
            return stock.info
        except Exception as e:
            print(f"获取 {ticker} 信息时出错: {e}")
            return {}

