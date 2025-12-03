import sys
import os
# 强制设置标准输出编码为 utf-8，解决 Windows 控制台中文乱码问题
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass 

from data_loader import DataLoader
from analysis import TechnicalAnalyzer
from llm_advisor import LLMAdvisor

# ==========================================
# 配置区域
# 你可以在这里直接填入 API Key，或者设置环境变量
# DeepSeek Example:
# LLM_API_KEY = "sk-xxxxxxxx"
# LLM_BASE_URL = "https://api.deepseek.com/v1"
# LLM_MODEL = "deepseek-chat"
# ==========================================

def main():
    loader = DataLoader()
    
    # 初始化 AI 顾问 (尝试从环境变量读取，也可以在这里硬编码传入)
    # 如果你想测试 DeepSeek，可以在这里手动传入参数:
    # advisor = LLMAdvisor(api_key="你的key", base_url="https://api.deepseek.com/v1", model="deepseek-chat")
    advisor = LLMAdvisor() 
    
    # 测试股票列表
    tickers = ['AAPL', '0700.HK']
    
    print("=== BotInvest 智能助理 (Demo) ===")
    print("注意: 如果网络受限，将使用本地模拟数据演示。")
    
    for ticker in tickers:
        print(f"\n-------------------------------")
        print(f"正在分析: {ticker}")
        
        # 1. 获取历史数据
        df = loader.get_stock_history(ticker, period="3mo") # 获取更长的数据以计算支撑/阻力位
        
        if df is not None:
            # 2. 技术分析
            analyzer = TechnicalAnalyzer(df)
            analyzer.add_sma(period=5)
            analyzer.add_rsi(period=14) 
            analyzer.add_atr(period=14)
            analyzer.add_support_resistance(window=20)
            
            result = analyzer.get_analysis()
            
            # 打印最近的记录
            print(f"成功获取 {len(df)} 条交易记录")
            print("最新技术指标分析:")
            
            cols = ['Date', 'Close', 'SMA_5', 'RSI', 'Support_Level', 'Resistance_Level']
            display_cols = [c for c in cols if c in result.columns]
            print(result[display_cols].tail(5).to_string(index=False))
            
            # 3. 准备数据给 AI
            latest = result.iloc[-1]
            prev = result.iloc[-2] if len(result) > 1 else latest
            
            price_data = {
                "current_price": f"{latest['Close']:.2f}",
                "change_percent": f"{((latest['Close'] - prev['Close']) / prev['Close'] * 100):.2f}"
            }
            
            indicators = {
                "sma_5": f"{latest.get('SMA_5', 0):.2f}",
                "rsi": f"{latest.get('RSI', 0):.2f}",
                "atr": f"{latest.get('ATR', 0):.2f}",
                "support": f"{latest.get('Support_Level', 0):.2f}",
                "resistance": f"{latest.get('Resistance_Level', 0):.2f}"
            }
            
            # 4. 调用 LLM 进行分析
            print("\n>> 正在请求 AI 投资顾问分析...")
            ai_analysis = advisor.get_analysis(ticker, price_data, indicators)
            print(f"\n[AI 分析报告]\n{ai_analysis}")
                
        else:
            print("数据获取失败")

if __name__ == "__main__":
    main()
