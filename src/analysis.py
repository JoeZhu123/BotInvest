import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    def __init__(self, dataframe: pd.DataFrame):
        """
        初始化分析器
        :param dataframe: 包含 'Close', 'High', 'Low' 列的 DataFrame
        """
        self.df = dataframe.copy()

    def add_sma(self, period: int = 5):
        """
        计算简单移动平均线 (SMA)
        """
        col_name = f'SMA_{period}'
        self.df[col_name] = self.df['Close'].rolling(window=period).mean()
        return self.df

    def add_rsi(self, period: int = 14):
        """
        计算相对强弱指数 (RSI)
        """
        delta = self.df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        rs = avg_gain / avg_loss
        self.df['RSI'] = 100 - (100 / (1 + rs))
        return self.df

    def add_atr(self, period: int = 14):
        """
        计算平均真实波幅 (ATR) - 用于确定止损和波动范围
        """
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.df['ATR'] = tr.rolling(window=period).mean()
        return self.df

    def add_support_resistance(self, window: int = 20):
        """
        计算近期支撑位和阻力位 (基于过去N天的最低/最高点)
        """
        self.df['Support_Level'] = self.df['Low'].rolling(window=window).min()
        self.df['Resistance_Level'] = self.df['High'].rolling(window=window).max()
        return self.df

    def get_analysis(self) -> pd.DataFrame:
        return self.df
