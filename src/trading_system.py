import json
import os
import pandas as pd
from datetime import datetime
from data_loader import DataLoader

class TradingAccount:
    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions = {} # {ticker: {"qty": 0, "avg_cost": 0.0}}
        self.history = []   # [{"date":..., "action":..., "ticker":..., "price":..., "qty":...}]
        
    def total_value(self, current_prices: dict) -> float:
        """
        计算总资产 (现金 + 持仓市值)
        """
        market_value = 0.0
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos['avg_cost']) # 如果没拿到现价，暂时用成本价估算
            market_value += pos['qty'] * price
        return self.cash + market_value

class BaseTrader:
    def buy(self, ticker: str, qty: int, price: float): raise NotImplementedError
    def sell(self, ticker: str, qty: int, price: float): raise NotImplementedError
    def get_account(self) -> TradingAccount: raise NotImplementedError

class PaperTrader(BaseTrader):
    """
    本地模拟交易器 - 将数据保存在 JSON 文件中
    """
    def __init__(self, data_file="portfolio.json"):
        self.data_file = data_file
        self.account = self._load_account()

    def _load_account(self) -> TradingAccount:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    acc = TradingAccount(data.get('cash', 100000.0))
                    acc.positions = data.get('positions', {})
                    acc.history = data.get('history', [])
                    return acc
            except Exception:
                return TradingAccount()
        return TradingAccount()

    def _save_account(self):
        data = {
            "cash": self.account.cash,
            "positions": self.account.positions,
            "history": self.account.history
        }
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def buy(self, ticker: str, qty: int, price: float):
        cost = qty * price
        if cost > self.account.cash:
            return False, "资金不足"
        
        # 扣款
        self.account.cash -= cost
        
        # 更新持仓
        if ticker not in self.account.positions:
            self.account.positions[ticker] = {"qty": 0, "avg_cost": 0.0}
            
        pos = self.account.positions[ticker]
        # 重新计算平均成本
        total_cost = (pos['qty'] * pos['avg_cost']) + cost
        pos['qty'] += qty
        pos['avg_cost'] = total_cost / pos['qty']
        
        # 记录历史
        self._log_trade("BUY", ticker, qty, price)
        self._save_account()
        return True, "买入成功"

    def sell(self, ticker: str, qty: int, price: float):
        if ticker not in self.account.positions or self.account.positions[ticker]['qty'] < qty:
            return False, "持仓不足"
            
        income = qty * price
        
        # 收款
        self.account.cash += income
        
        # 更新持仓
        pos = self.account.positions[ticker]
        pos['qty'] -= qty
        if pos['qty'] == 0:
            del self.account.positions[ticker]
            
        # 记录历史
        self._log_trade("SELL", ticker, qty, price)
        self._save_account()
        return True, "卖出成功"

    def _log_trade(self, action, ticker, qty, price):
        self.account.history.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "ticker": ticker,
            "qty": qty,
            "price": price,
            "amount": qty * price
        })

    def get_account(self) -> TradingAccount:
        return self.account

