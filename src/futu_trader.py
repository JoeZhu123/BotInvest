try:
    from futu import *
except ImportError:
    print("警告: 未安装 futu-api，实盘交易功能不可用。请运行 pip install futu-api")
    # 定义占位符以防报错
    class OpenTradeContext: pass
    RET_OK = 0
    TrdSide = None
    TrdEnv = None

from trading_system import BaseTrader, TradingAccount
import time

class FutuTrader(BaseTrader):
    """
    富途实盘交易适配器
    支持 美股(US) 和 港股(HK)
    """
    def __init__(self, host='127.0.0.1', port=11111, pwd_unlock=None, market='US'):
        self.host = host
        self.port = port
        self.pwd_unlock = pwd_unlock
        self.market = market # 主要操作市场，但这只是默认，我们会尝试连接所有
        
        # 缓存连接上下文
        self.ctx_us = None
        self.ctx_hk = None
        self.ctx_cn = None
        
        self._connect()

    def _connect(self):
        try:
            # 建立美股连接
            self.ctx_us = OpenTradeContext(host=self.host, port=self.port, filter_trdmarket=TrdMarket.US)
            # 建立港股连接
            self.ctx_hk = OpenTradeContext(host=self.host, port=self.port, filter_trdmarket=TrdMarket.HK)
            # 建立A股连接 (沪深)
            self.ctx_cn = OpenTradeContext(host=self.host, port=self.port, filter_trdmarket=TrdMarket.CN)
            
            # 解锁交易 (如果提供了密码)
            if self.pwd_unlock:
                if self.ctx_us: self.ctx_us.unlock_trade(self.pwd_unlock)
                if self.ctx_hk: self.ctx_hk.unlock_trade(self.pwd_unlock)
                if self.ctx_cn: self.ctx_cn.unlock_trade(self.pwd_unlock)
                
            print("Futu OpenD 连接成功")
        except Exception as e:
            print(f"Futu OpenD 连接失败: {e}")

    def _get_ctx(self, ticker):
        """根据股票代码返回对应的上下文"""
        if '.' not in ticker: # 默认美股，如 AAPL
            return self.ctx_us, "US." + ticker
        
        suffix = ticker.split('.')[-1]
        if suffix in ['HK']:
            return self.ctx_hk, "HK." + ticker.replace('.HK', '')
        elif suffix in ['SS', 'SH']:
            return self.ctx_cn, "SH." + ticker.replace('.SS', '').replace('.SH', '')
        elif suffix in ['SZ']:
            return self.ctx_cn, "SZ." + ticker.replace('.SZ', '')
        else:
            return self.ctx_us, "US." + ticker

    def get_account(self) -> TradingAccount:
        acc = TradingAccount(0.0)
        acc.positions = {}
        
        contexts = [self.ctx_us, self.ctx_hk, self.ctx_cn]
        
        for ctx in contexts:
            if ctx is None: continue
            
            # 1. 获取资金
            ret, data = ctx.accinfo_query(trd_env=TrdEnv.REAL)
            if ret == RET_OK:
                # 简单累加各市场的现金 (注意：这里直接把数字加在一起了，实际上应该汇率换算)
                # 富途通常会把总资产换算成一个币种，这里取 total_assets 比较方便
                # 但为了简单，我们只取 'cash'
                acc.cash += data['cash'].sum()

            # 2. 获取持仓
            ret, pos_data = ctx.position_list_query(trd_env=TrdEnv.REAL)
            if ret == RET_OK:
                for _, row in pos_data.iterrows():
                    # 转换代码格式 Futu -> BotInvest
                    code = row['code']
                    qty = row['qty']
                    cost = row['cost_price']
                    
                    # 简单映射回 BotInvest 格式
                    if "US." in code: ticker = code.replace("US.", "")
                    elif "HK." in code: ticker = code.replace("HK.", "") + ".HK"
                    elif "SH." in code: ticker = code.replace("SH.", "") + ".SS"
                    elif "SZ." in code: ticker = code.replace("SZ.", "") + ".SZ"
                    else: ticker = code
                    
                    if qty > 0: # 只显示多头
                        acc.positions[ticker] = {
                            "qty": float(qty),
                            "avg_cost": float(cost)
                        }
        return acc

    def buy(self, ticker: str, qty: int, price: float):
        ctx, futu_code = self._get_ctx(ticker)
        if ctx is None: return False, "连接未建立"
        
        ret, data = ctx.place_order(
            price=price, 
            qty=qty, 
            code=futu_code, 
            trd_side=TrdSide.BUY,
            trd_env=TrdEnv.REAL
        )
        if ret == RET_OK:
            return True, f"下单成功: {data['order_id'][0]}" # 修正取值
        else:
            return False, f"下单失败: {data}"

    def sell(self, ticker: str, qty: int, price: float):
        ctx, futu_code = self._get_ctx(ticker)
        if ctx is None: return False, "连接未建立"
        
        ret, data = ctx.place_order(
            price=price, 
            qty=qty, 
            code=futu_code, 
            trd_side=TrdSide.SELL, 
            trd_env=TrdEnv.REAL
        )
        if ret == RET_OK:
            return True, f"下单成功: {data['order_id'][0]}"
        else:
            return False, f"下单失败: {data}"

    def close(self):
        if self.ctx_us: self.ctx_us.close()
        if self.ctx_hk: self.ctx_hk.close()
        if self.ctx_cn: self.ctx_cn.close()

