import pandas as pd
from data_loader import DataLoader
from analysis import TechnicalAnalyzer
from stock_pool import StockPool

class Screener:
    def __init__(self):
        self.loader = DataLoader()
        self.pool = StockPool()

    def run_screener(self, progress_callback=None):
        """
        运行选股器
        :param progress_callback: 回调函数，用于更新 UI 进度条 (current, total, current_ticker)
        """
        tickers = self.pool.get_all_tickers()
        results = {
            "long_term": [], # 适合长期持有的
            "short_term": [], # 适合短期交易的
            "watch_list": []  # 其他值得关注的
        }
        
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(i, total, ticker)
                
            # 获取数据 (使用较短周期以加快速度，但为了MA60需要至少3个月)
            df = self.loader.get_stock_history(ticker, period="6mo")
            
            if df is None or df.empty or len(df) < 60:
                continue
                
            # 计算指标
            analyzer = TechnicalAnalyzer(df)
            analyzer.add_sma(period=20)
            analyzer.add_sma(period=60)
            analyzer.add_rsi(period=14)
            df_res = analyzer.get_analysis()
            
            latest = df_res.iloc[-1]
            prev = df_res.iloc[-2]
            
            price = latest['Close']
            sma20 = latest['SMA_20']
            sma60 = latest['SMA_60']
            rsi = latest['RSI']
            
            # --- 筛选逻辑 ---
            
            item = {
                "ticker": ticker,
                "price": price,
                "rsi": rsi,
                "trend": "Bullish" if price > sma60 else "Bearish"
            }
            
            # 1. 长期潜力 (趋势向上 + 健康回调)
            # 价格在 60日均线之上 (长期趋势好) 且 RSI 适中 (没有被炒作过头)
            if price > sma60 and 40 < rsi < 70:
                item['reason'] = "长期上升趋势稳健，估值适中"
                results['long_term'].append(item)
                
            # 2. 短期机会 (超卖反弹 或 突破)
            # 超卖
            elif rsi < 30:
                item['reason'] = "RSI超卖 (<30)，存在反弹需求"
                results['short_term'].append(item)
            # 突破
            elif price > sma20 and prev['Close'] <= prev['SMA_20']:
                 item['reason'] = "放量突破 20日均线"
                 results['short_term'].append(item)
                 
            else:
                results['watch_list'].append(item)
                
        return results

