import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import DataLoader
from analysis import TechnicalAnalyzer
from llm_advisor import LLMAdvisor
from user_profile import UserProfile
from screener import Screener
from trading_system import PaperTrader
import os

# 页面配置
st.set_page_config(
    page_title="BotInvest 智能交易助理",
    page_icon="📈",
    layout="wide"
)

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "screener_results" not in st.session_state:
    st.session_state.screener_results = None
if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader()

def main():
    # 加载用户档案
    profile = UserProfile()
    trader = st.session_state.trader

    # --- 侧边栏配置 ---
    with st.sidebar:
        st.title("⚙️ 设置")
        
        api_key = st.text_input("LLM API Key", value=os.getenv("LLM_API_KEY", ""), type="password")
        base_url = st.text_input("Base URL (Optional)", value=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
        model_name = st.text_input("Model Name", value=os.getenv("LLM_MODEL", "gpt-3.5-turbo"))
        
        st.divider()
        
        ticker = st.text_input("股票代码", value="AAPL").upper()
        period = st.selectbox("时间周期", ["1mo", "3mo", "6mo", "1y"], index=1)
        
        if st.button("清空对话历史"):
            st.session_state.messages = []
            st.rerun()

    # --- 主界面布局 ---
    st.title(f"BotInvest 智能交易助理")
    
    # 使用 Tab 分隔功能
    tab_analysis, tab_trading, tab_screener, tab_philosophy = st.tabs([
        "📈 市场分析 & AI 对话", 
        "💸 实盘/模拟交易",
        "📅 智能选股推荐", 
        "📝 我的投资思想"
    ])

    # === Tab 2: 实盘/模拟交易 ===
    with tab_trading:
        st.header("实盘/模拟交易中心 (Trading Desk)")
        
        # 获取最新账户信息
        acc = trader.get_account()
        
        # 尝试获取持仓股票的现价，以计算市值
        loader = DataLoader()
        current_prices = {}
        if acc.positions:
            with st.spinner("正在更新持仓市值..."):
                for t in acc.positions.keys():
                    df_p = loader.get_stock_history(t, period="1d")
                    if df_p is not None and not df_p.empty:
                        current_prices[t] = df_p.iloc[-1]['Close']
        
        total_val = acc.total_value(current_prices)
        
        # 1. 账户概览
        col_a1, col_a2, col_a3 = st.columns(3)
        col_a1.metric("总资产 (Total Value)", f"${total_val:,.2f}")
        col_a2.metric("可用现金 (Cash)", f"${acc.cash:,.2f}")
        col_a3.metric("持仓数量", len(acc.positions))
        
        st.divider()
        
        # 2. 交易操作区
        col_trade_l, col_trade_r = st.columns([1, 2])
        
        with col_trade_l:
            st.subheader("下单 (Order Entry)")
            trade_ticker = st.text_input("交易标的", value=ticker).upper()
            trade_action = st.radio("方向", ["买入 (Buy)", "卖出 (Sell)"], horizontal=True)
            
            # 获取实时价格作为参考
            ref_price = 0.0
            if trade_ticker in current_prices:
                ref_price = current_prices[trade_ticker]
            else:
                # 尝试获取
                df_ref = loader.get_stock_history(trade_ticker, period="1d")
                if df_ref is not None and not df_ref.empty:
                    ref_price = df_ref.iloc[-1]['Close']
            
            if ref_price > 0:
                st.info(f"当前参考价: ${ref_price:.2f}")
            
            trade_price = st.number_input("价格 (Price)", min_value=0.01, value=ref_price if ref_price > 0 else 100.0, step=0.1)
            trade_qty = st.number_input("数量 (Qty)", min_value=1, value=10, step=1)
            
            if st.button("提交订单 (Submit Order)", type="primary"):
                if "买入" in trade_action:
                    success, msg = trader.buy(trade_ticker, trade_qty, trade_price)
                else:
                    success, msg = trader.sell(trade_ticker, trade_qty, trade_price)
                
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with col_trade_r:
            st.subheader("当前持仓 (Positions)")
            if acc.positions:
                pos_data = []
                for t, p in acc.positions.items():
                    curr_p = current_prices.get(t, p['avg_cost'])
                    mkt_val = p['qty'] * curr_p
                    pnl = (curr_p - p['avg_cost']) * p['qty']
                    pnl_pct = (curr_p - p['avg_cost']) / p['avg_cost'] * 100 if p['avg_cost'] > 0 else 0
                    
                    pos_data.append({
                        "标的": t,
                        "持仓量": p['qty'],
                        "成本价": f"${p['avg_cost']:.2f}",
                        "现价": f"${curr_p:.2f}",
                        "市值": f"${mkt_val:,.2f}",
                        "浮动盈亏": f"${pnl:,.2f} ({pnl_pct:.2f}%)"
                    })
                st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
            else:
                st.info("暂无持仓")
                
            st.subheader("交易记录 (History)")
            if acc.history:
                hist_df = pd.DataFrame(acc.history)
                st.dataframe(hist_df.sort_values("date", ascending=False), use_container_width=True)
            else:
                st.write("暂无交易记录")


    # === Tab 3: 智能选股推荐 ===
    with tab_screener:
        st.header("智能选股推荐 (Smart Screener)")
        st.markdown("系统将扫描美股和港股的热门标的，基于**技术指标**为您筛选出潜在机会。")
        
        if st.button("🚀 开始扫描 (可能需要几分钟)"):
            screener = Screener()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total, ticker):
                progress = int((current / total) * 100)
                progress_bar.progress(progress)
                status_text.text(f"正在分析: {ticker} ({current+1}/{total})...")
            
            try:
                results = screener.run_screener(progress_callback=update_progress)
                st.session_state.screener_results = results
                progress_bar.empty()
                status_text.success("扫描完成！")
            except Exception as e:
                st.error(f"扫描过程中出错: {e}")

        # 显示结果
        if st.session_state.screener_results:
            res = st.session_state.screener_results
            
            col_long, col_short = st.columns(2)
            
            with col_long:
                st.subheader("💎 长期持有潜力 (Long-term)")
                st.info("筛选逻辑: 股价 > 60日均线 (趋势向上) 且 RSI < 70 (估值适中)")
                if res['long_term']:
                    df_long = pd.DataFrame(res['long_term'])
                    st.dataframe(
                        df_long[['ticker', 'price', 'rsi', 'reason']], 
                        use_container_width=True,
                        column_config={
                            "ticker": "代码",
                            "price": st.column_config.NumberColumn("价格", format="$%.2f"),
                            "rsi": st.column_config.NumberColumn("RSI", format="%.2f"),
                            "reason": "推荐理由"
                        }
                    )
                else:
                    st.write("暂无符合条件的标的。")

            with col_short:
                st.subheader("⚡ 短期交易机会 (Short-term)")
                st.info("筛选逻辑: RSI < 30 (超卖反弹) 或 突破20日均线")
                if res['short_term']:
                    df_short = pd.DataFrame(res['short_term'])
                    st.dataframe(
                        df_short[['ticker', 'price', 'rsi', 'reason']], 
                        use_container_width=True,
                        column_config={
                            "ticker": "代码",
                            "price": st.column_config.NumberColumn("价格", format="$%.2f"),
                            "rsi": st.column_config.NumberColumn("RSI", format="%.2f"),
                            "reason": "推荐理由"
                        }
                    )
                else:
                    st.write("暂无符合条件的标的。")
            
            with st.expander("👀 观察列表 (Watch List)"):
                if res['watch_list']:
                    st.dataframe(pd.DataFrame(res['watch_list']))

    # === Tab 4: 投资思想管理 ===
    with tab_philosophy:
        st.header("我的投资原则 (Investment Principles)")
        st.info("在这里记录您的核心交易纪律。AI 顾问在为您提供建议时，会严格参考这些原则。")
        
        col_p1, col_p2 = st.columns([1, 1])
        
        with col_p1:
            st.subheader("核心原则")
            principles_text = st.text_area(
                "每一行代表一条原则", 
                value=profile.get_principles_text(),
                height=300,
                placeholder="例如：\n不追高买入\n单笔亏损不超过 2%\n只做上升趋势"
            )
            if st.button("保存原则"):
                profile.save_principles(principles_text)
                st.success("原则已更新！AI 将在下次对话中应用这些规则。")
        
        with col_p2:
            st.subheader("策略笔记")
            notes_text = st.text_area(
                "记录您的感悟或特定策略",
                value=profile.get_notes(),
                height=300
            )
            if st.button("保存笔记"):
                profile.save_notes(notes_text)
                st.success("笔记已保存。")

    # === Tab 1: 市场分析 ===
    with tab_analysis:
        st.subheader(f"📊 {ticker} 行情分析")
        
        # 1. 获取数据
        loader = DataLoader()
        with st.spinner('正在加载数据...'):
            df = loader.get_stock_history(ticker, period=period)
        
        if df is None or df.empty:
            st.error(f"无法获取 {ticker} 的数据，请检查代码是否正确或网络连接。")
            return

        # 2. 技术分析
        analyzer = TechnicalAnalyzer(df)
        analyzer.add_sma(period=5)
        analyzer.add_sma(period=20)
        analyzer.add_rsi(period=14)
        analyzer.add_atr(period=14)
        analyzer.add_support_resistance(window=20)
        result = analyzer.get_analysis()

        # 3. 绘制图表 (K线 + 均线)
        fig = go.Figure()
        
        # K线
        fig.add_trace(go.Candlestick(
            x=result['Date'],
            open=result['Open'], high=result['High'],
            low=result['Low'], close=result['Close'],
            name='K线'
        ))
        
        # 均线
        fig.add_trace(go.Scatter(x=result['Date'], y=result['SMA_5'], line=dict(color='orange', width=1), name='MA5'))
        fig.add_trace(go.Scatter(x=result['Date'], y=result['SMA_20'], line=dict(color='blue', width=1), name='MA20'))
        
        fig.update_layout(
            title=f"{ticker} 股价走势",
            xaxis_title="日期",
            yaxis_title="价格",
            height=500,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 4. 指标概览卡片
        latest = result.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("最新收盘价", f"${latest['Close']:.2f}")
        col2.metric("RSI (14)", f"{latest['RSI']:.2f}")
        col3.metric("支撑位", f"${latest['Support_Level']:.2f}")
        col4.metric("阻力位", f"${latest['Resistance_Level']:.2f}")

        st.divider()

        # --- AI 聊天助手 ---
        st.subheader("🤖 AI 交易顾问 (基于您的原则)")

        # 构建上下文数据字符串 (供 AI 参考)
        context_str = f"""
        标的: {ticker}
        最新价格: {latest['Close']:.2f}
        RSI(14): {latest['RSI']:.2f}
        MA5: {latest['SMA_5']:.2f}
        MA20: {latest['SMA_20']:.2f}
        ATR(14): {latest['ATR']:.2f}
        短期支撑位: {latest['Support_Level']:.2f}
        短期阻力位: {latest['Resistance_Level']:.2f}
        """
        
        # 获取用户当前的原则文本
        user_principles_context = profile.get_principles_text()

        # 初始化 Advisor
        advisor = LLMAdvisor(api_key=api_key, base_url=base_url, model=model_name)

        # 显示历史消息
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 处理用户输入
        if prompt := st.chat_input("问问 AI 关于这只股票的建议..."):
            # 1. 显示用户消息
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # 2. 获取 AI 回答
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # 流式输出 (传入 context_data 和 user_principles)
                stream = advisor.get_chat_response(
                    st.session_state.messages, 
                    context_data=context_str,
                    user_profile=user_principles_context
                )
                
                for chunk in stream:
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
            
            # 3. 保存 AI 回答
            st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()
