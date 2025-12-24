import pandas as pd
import os
import time
from typing import Optional, List

import yfinance as yf

from market_data_providers import (
    AlphaVantageProvider,
    FutuQuoteProvider,
    StooqProvider,
    YahooFinanceProvider,
)

class DataLoader:
    def __init__(self):
        pass

    def normalize_ticker(self, ticker: str) -> str:
        """
        兼容用户输入的多种代码格式：
        - BotInvest / Yahoo: AAPL, 0700.HK, 600519.SS, 300750.SZ
        - Futu: US.AAPL, HK.00700, SH.600519, SZ.300750
        """
        t = (ticker or "").strip().upper()
        if not t:
            return t

        # Futu -> Yahoo
        if t.startswith("US."):
            return t.replace("US.", "")
        if t.startswith("HK."):
            code = t.replace("HK.", "").lstrip("0")
            if code == "":
                code = "0"
            return f"{code}.HK"
        if t.startswith("SH."):
            code = t.replace("SH.", "")
            return f"{code}.SS"
        if t.startswith("SZ."):
            code = t.replace("SZ.", "")
            return f"{code}.SZ"

        return t

    def get_stock_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        allow_fallback: bool = False,
        data_source: str = "auto",
        futu_host: str | None = None,
        futu_port: int | None = None,
        futu_enabled: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        """
        ticker = self.normalize_ticker(ticker)
        ds = (data_source or "auto").lower().strip()
        print(f"正在获取 {ticker} 的数据... (source={ds})")

        def try_provider(provider_name: str, provider_factory):
            try:
                provider_obj = provider_factory()
                df0 = provider_obj.get_history(ticker, period=period, interval=interval)
                if df0 is not None and not df0.empty:
                    # 在 DataFrame 上标注数据源，便于 UI 显示
                    df0.attrs["data_source"] = provider_name
                    return df0
            except Exception as e:
                print(f"[{provider_name}] 获取失败: {e}")
            return None

        # 1) 指定数据源
        if ds != "auto":
            if ds == "futu":
                df = try_provider("futu", lambda: FutuQuoteProvider(host=futu_host, port=futu_port))
            elif ds == "yahoo":
                df = try_provider("yahoo", lambda: YahooFinanceProvider())
            elif ds == "stooq":
                df = try_provider("stooq", lambda: StooqProvider())
            elif ds == "alphavantage":
                df = try_provider("alphavantage", lambda: AlphaVantageProvider())
            else:
                df = None

            if df is not None:
                return df

        # 2) 自动模式：优先 Futu Quote（避免 Yahoo 限流），然后 Yahoo，再 Stooq/AlphaVantage
        df = None
        # Futu
        if futu_enabled:
            df = try_provider("futu", lambda: FutuQuoteProvider(host=futu_host, port=futu_port))
            if df is not None:
                return df

        # Yahoo：带简单重试，缓解偶发限流/网络抖动
        try:
            provider = YahooFinanceProvider()
            last_err: Exception | None = None
            for attempt in range(3):
                try:
                    df = provider.get_history(ticker, period=period, interval=interval)
                    if df is not None and not df.empty:
                        df.attrs["data_source"] = "yahoo"
                        return df
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    msg = str(e)
                    if "Too Many Requests" in msg or "Rate limited" in msg:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise
            if last_err is not None:
                print(f"[yahoo] 获取失败: {last_err}")
        except Exception as e:
            print(f"[yahoo] 获取失败: {e}")

        # Stooq（主要覆盖美股）
        df = try_provider("stooq", lambda: StooqProvider())
        if df is not None:
            return df

        # AlphaVantage（需要 key，主要覆盖美股）
        df = try_provider("alphavantage", lambda: AlphaVantageProvider())
        if df is not None:
            return df

        # 3) 本地演示数据（可选）
        if allow_fallback and os.path.exists("data/sample_data.csv"):
            print(f"切换到本地测试数据: data/sample_data.csv")
            df = pd.read_csv("data/sample_data.csv")
            df.attrs["data_source"] = "local_sample"
            return df

        return None

    def get_stock_info(self, ticker: str) -> dict:
        """
        获取股票基本信息
        """
        try:
            ticker = self.normalize_ticker(ticker)
            stock = yf.Ticker(ticker)
            return stock.info
        except Exception as e:
            print(f"获取 {ticker} 信息时出错: {e}")
            return {}

    def get_stock_news(self, ticker: str) -> List[dict]:
        """
        获取股票相关新闻
        :return: List of dicts {'title': str, 'link': str, 'publisher': str, 'providerPublishTime': int}
        """
        try:
            ticker = self.normalize_ticker(ticker)
            stock = yf.Ticker(ticker)
            news = stock.news
            return news if news else []
        except Exception as e:
            print(f"获取 {ticker} 新闻时出错: {e}")
            return []
