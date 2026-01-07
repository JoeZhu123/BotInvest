try:
    # futu-api 9.x 中证券交易使用 OpenSecTradeContext（不是 OpenTradeContext）
    from futu import OpenSecTradeContext, TrdMarket, TrdSide, TrdEnv, RET_OK, ModifyOrderOp
except ImportError:
    print("警告: 未安装 futu-api，实盘交易功能不可用。请运行 pip install futu-api")
    # 定义占位符以防报错
    OpenSecTradeContext = None
    TrdMarket = None
    TrdSide = None
    TrdEnv = None
    RET_OK = 0
    ModifyOrderOp = None

from trading_system import BaseTrader, TradingAccount
import time
from market_data_providers import to_futu_code
import pandas as pd

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
            if OpenSecTradeContext is None:
                raise RuntimeError("futu-api 未安装或导入失败")

            # 建立证券交易连接（不同市场用 filter_trdmarket 区分）
            self.ctx_us = OpenSecTradeContext(host=self.host, port=self.port, filter_trdmarket=TrdMarket.US)
            self.ctx_hk = OpenSecTradeContext(host=self.host, port=self.port, filter_trdmarket=TrdMarket.HK)
            self.ctx_cn = OpenSecTradeContext(host=self.host, port=self.port, filter_trdmarket=TrdMarket.CN)
            
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
        t = (ticker or "").strip().upper()
        futu_code = to_futu_code(t)

        if futu_code.startswith("HK."):
            return self.ctx_hk, futu_code
        if futu_code.startswith(("SH.", "SZ.")):
            return self.ctx_cn, futu_code
        # 默认美股
        return self.ctx_us, futu_code

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

    def list_orders(self):
        """
        查询当前订单（实盘）。返回 pandas.DataFrame（可能为空）
        """
        frames = []
        for ctx in [self.ctx_us, self.ctx_hk, self.ctx_cn]:
            if ctx is None:
                continue
            ret, data = ctx.order_list_query(trd_env=TrdEnv.REAL)
            if ret == RET_OK and data is not None and not data.empty:
                frames.append(data)
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
        return df

    def cancel_order(self, order_id: str | int):
        """
        撤单（实盘）。先定位 order_id 属于哪个 market 的 ctx，再执行撤单。
        """
        if ModifyOrderOp is None:
            return False, "futu-api 未正确导入"

        oid = str(order_id).strip()
        if not oid:
            return False, "order_id 为空"

        # 在各市场中查找订单
        for ctx in [self.ctx_us, self.ctx_hk, self.ctx_cn]:
            if ctx is None:
                continue
            ret, data = ctx.order_list_query(trd_env=TrdEnv.REAL)
            if ret != RET_OK or data is None or data.empty:
                continue
            if "order_id" in data.columns and (data["order_id"].astype(str) == oid).any():
                ret2, data2 = ctx.modify_order(
                    ModifyOrderOp.CANCEL,
                    order_id=oid,
                    qty=0,
                    price=0,
                    trd_env=TrdEnv.REAL,
                )
                if ret2 == RET_OK:
                    return True, "撤单成功"
                return False, f"撤单失败: {data2}"

        return False, "未找到该订单（可能已成交/已撤/不在当前市场连接）"

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
            try:
                order_id = data["order_id"].iloc[0]
            except Exception:
                order_id = ""
            return True, f"下单成功: {order_id}"
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
            try:
                order_id = data["order_id"].iloc[0]
            except Exception:
                order_id = ""
            return True, f"下单成功: {order_id}"
        else:
            return False, f"下单失败: {data}"

    def close(self):
        if self.ctx_us: self.ctx_us.close()
        if self.ctx_hk: self.ctx_hk.close()
        if self.ctx_cn: self.ctx_cn.close()

