from __future__ import annotations

import os
import time
import io
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
import requests


def _period_to_days(period: str) -> int:
    p = (period or "").lower().strip()
    mapping = {
        "1mo": 35,
        "3mo": 120,
        "6mo": 220,
        "1y": 420,
        "2y": 800,
        "5y": 2000,
        "10y": 4000,
        "ytd": 420,
        "max": 8000,
    }
    return mapping.get(p, 420)


def _normalize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    统一成: Date/Open/High/Low/Close/Volume
    """
    if df is None or df.empty:
        return df

    # 常见列名映射
    rename_map = {
        "time_key": "Date",
        "date": "Date",
        "datetime": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # 只保留需要的列（如果存在）
    cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    if cols:
        df = df[cols]
    return df


def to_futu_code(yahoo_ticker: str) -> str:
    """
    将 Yahoo/BotInvest 标准格式转换为 Futu code
    - AAPL -> US.AAPL
    - 0700.HK/700.HK -> HK.00700
    - 600519.SS -> SH.600519
    - 300750.SZ -> SZ.300750
    """
    t = (yahoo_ticker or "").strip().upper()
    if not t:
        return t

    # 已经是 futu
    if t.startswith(("US.", "HK.", "SH.", "SZ.")):
        return t

    if t.endswith(".HK"):
        code = t.replace(".HK", "")
        code = code.zfill(5)
        return f"HK.{code}"
    if t.endswith(".SS") or t.endswith(".SH"):
        code = t.split(".")[0]
        return f"SH.{code}"
    if t.endswith(".SZ"):
        code = t.split(".")[0]
        return f"SZ.{code}"
    # 默认美股
    return f"US.{t}"


class MarketDataProvider:
    name: str

    def get_history(self, yahoo_ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        raise NotImplementedError


class YahooFinanceProvider(MarketDataProvider):
    name = "yahoo"

    def __init__(self):
        import yfinance as yf

        self.yf = yf

    def get_history(self, yahoo_ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        stock = self.yf.Ticker(yahoo_ticker)
        df = stock.history(period=period, interval=interval)
        if df is None or df.empty:
            return None
        df = df.reset_index()
        return _normalize_ohlcv_df(df)


class FutuQuoteProvider(MarketDataProvider):
    name = "futu"

    def __init__(self, host: str | None = None, port: int | None = None):
        from futu import OpenQuoteContext, RET_OK, KLType, AuType

        self.OpenQuoteContext = OpenQuoteContext
        self.RET_OK = RET_OK
        self.KLType = KLType
        self.AuType = AuType

        self.host = host or os.getenv("FUTU_OPEND_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("FUTU_OPEND_PORT", "11111"))
        self.quote_ctx = self.OpenQuoteContext(host=self.host, port=self.port)

    def get_history(self, yahoo_ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        # 目前我们只实现日线（BotInvest 的指标也主要是日线）
        # 如需分钟线后续可以扩展 KLType
        if (interval or "1d").lower() not in ("1d", "1day", "day", "1d "):
            interval = "1d"

        end = pd.Timestamp.utcnow().tz_localize(None)
        start = end - pd.Timedelta(days=_period_to_days(period))

        code = to_futu_code(yahoo_ticker)
        ret, data = self.quote_ctx.request_history_kline(
            code=code,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            ktype=self.KLType.K_DAY,
            autype=self.AuType.QFQ,
        )
        if ret != self.RET_OK or data is None or data.empty:
            return None
        df = data.copy()
        # futu: time_key/open/high/low/close/volume
        df = _normalize_ohlcv_df(df)
        return df

    def close(self):
        try:
            self.quote_ctx.close()
        except Exception:
            pass


def probe_futu_quote(host: str, port: int) -> tuple[bool, str]:
    """
    检测 Futu OpenD Quote 是否可用（不需要解锁交易）
    """
    try:
        from futu import OpenQuoteContext, RET_OK

        ctx = OpenQuoteContext(host=host, port=port)
        ret, data = ctx.get_global_state()
        ctx.close()
        if ret == RET_OK:
            return True, "OpenD 可用"
        return False, f"OpenD 返回异常: {data}"
    except Exception as e:
        return False, f"无法连接 OpenD: {e}"


class StooqProvider(MarketDataProvider):
    """
    备用数据源（主要覆盖美股；港股/A股覆盖不稳定）
    """

    name = "stooq"

    def get_history(self, yahoo_ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        # 仅日线
        if (interval or "1d").lower() not in ("1d", "1day", "day"):
            interval = "1d"

        t = yahoo_ticker.upper()
        # 仅处理美股（不带后缀）
        if "." in t:
            return None
        symbol = f"{t.lower()}.us"
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        df = pd.read_csv(io.StringIO(r.text))
        # stooq columns: Date,Open,High,Low,Close,Volume
        df = _normalize_ohlcv_df(df)
        if df is None or df.empty:
            return None
        # 截取 period 范围
        days = _period_to_days(period)
        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days)
        df = df[df["Date"] >= cutoff]
        return df


class AlphaVantageProvider(MarketDataProvider):
    name = "alphavantage"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY", "")

    def get_history(self, yahoo_ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        # 仅日线（免费额度也不适合频繁调用）
        if not self.api_key:
            return None
        t = yahoo_ticker.upper()
        if "." in t:
            # AlphaVantage 对非美股支持有限，这里先不处理
            return None
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": t,
            "apikey": self.api_key,
            "outputsize": "compact",
        }
        r = requests.get(url, params=params, timeout=25)
        if r.status_code != 200:
            return None
        j = r.json()
        key = "Time Series (Daily)"
        if key not in j:
            return None
        rows = []
        for dt, v in j[key].items():
            rows.append(
                {
                    "Date": dt,
                    "Open": float(v.get("1. open", 0)),
                    "High": float(v.get("2. high", 0)),
                    "Low": float(v.get("3. low", 0)),
                    "Close": float(v.get("4. close", 0)),
                    "Volume": float(v.get("6. volume", 0)),
                }
            )
        df = pd.DataFrame(rows)
        df = _normalize_ohlcv_df(df)
        df = df.sort_values("Date")
        # 截取 period
        days = _period_to_days(period)
        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days)
        df = df[df["Date"] >= cutoff]
        return df


def get_provider(provider_name: str) -> Optional[MarketDataProvider]:
    name = (provider_name or "auto").lower().strip()
    if name in ("futu", "futu_quote", "futuquote"):
        try:
            return FutuQuoteProvider()
        except Exception:
            return None
    if name in ("yahoo", "yf", "yfinance"):
        try:
            return YahooFinanceProvider()
        except Exception:
            return None
    if name in ("stooq",):
        return StooqProvider()
    if name in ("alphavantage", "alpha", "av"):
        return AlphaVantageProvider()
    return None


