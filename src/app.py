import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import DataLoader
from analysis import TechnicalAnalyzer
from llm_advisor import LLMAdvisor
from user_profile import UserProfile
from screener import Screener
from trading_system import PaperTrader
# 尝试导入 FutuTrader
try:
    from futu_trader import FutuTrader
except ImportError:
    FutuTrader = None

import os

# --- 页面基础配置 ---
st.set_page_config(
    page_title="BotInvest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 简洁 CSS 样式 (仅做微调) ---
def local_css():
    st.markdown("""
    <style>
        /* 侧边栏微调 */
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }
        
        /* 关键指标卡片样式 */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        /* 选项卡样式优化 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 0px;
            color: #555;
            font-weight: 500;
            border-bottom: 2px solid transparent;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: #0068c9;
            border-bottom: 2px solid #0068c9;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "screener_results" not in st.session_state:
    st.session_state.screener_results = None
if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader()
if "trading_mode" not in st.session_state:
    st.session_state.trading_mode = "Paper"

def main():
    profile = UserProfile()
    trader = st.session_state.trader

    # --- 侧边栏 ---
    with st.sidebar:
        st.header("⚙️ 设置")
        
        with st.expander("API 配置"):
            api_key = st.text_input("API Key", value=os.getenv("LLM_API_KEY", ""), type="password")
            base_url = st.text_input("Base URL", value=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
            model_name = st.text_input("Model", value=os.getenv("LLM_MODEL", "gpt-3.5-turbo"))
        
        st.markdown("### 交易通道")
        mode = st.selectbox("当前模式", ["Paper (模拟)", "Futu (富途实盘)"], 
                        index=0 if st.session_state.trading_mode == "Paper" else 1)
        
        if mode != st.session_state.trading_mode:
            st.session_state.trading_mode = mode
            if mode == "Paper":
                st.session_state.trader = PaperTrader()
                st.rerun()
            elif mode.startswith("Futu"):
                pass

        if st.session_state.trading_mode.startswith("Futu"):
            futu_host = st.text_input("OpenD Host", "127.0.0.1")
            futu_port = st.number_input("OpenD Port", 11111)
            futu_pwd = st.text_input("交易解锁密码", type="password")
            
            if st.button("连接富途", use_container_width=True):
                if FutuTrader:
                    try:
                        with st.spinner("正在连接..."):
                            st.session_state.trader = FutuTrader(host=futu_host, port=futu_port, pwd_unlock=futu_pwd)
                        st.success("已连接")
                        st.rerun()
                    except Exception as e:
                        st.error(f"连接失败: {e}")
                else:
                    st.error("未安装 futu-api")

        st.divider()
        
        st.markdown("### 标的选择")
        ticker = st.text_input("股票代码", value="AAPL", help="美股: AAPL; 港股: 0700.HK; A股: 600519.SS").upper()
        period = st.select_slider("时间周期", options=["1mo", "3mo", "6mo", "1y"], value="6mo")
        
        st.divider()
        if st.button("清空对话"):
            st.session_state.messages = []
            st.rerun()

    # --- 主界面 ---
    st.title(f"BotInvest 📈 {ticker}")
    
    # 定义 Tabs
    tab_analysis, tab_trading, tab_screener, tab_philosophy = st.tabs([
        "深度分析", 
        "交易终端",
        "选股扫描", 
        "投资原则"
    ])

    # === Tab 1: 市场分析 ===
    with tab_analysis:
        # 1. 获取数据
        loader = DataLoader()
        with st.spinner('加载数据...'):
            df = loader.get_stock_history(ticker, period=period)
        
        if df is None or df.empty:
            st.error(f"无法获取 {ticker} 数据")
            return

        # 2. 技术分析 (分步调用以防报错)
        analyzer = TechnicalAnalyzer(df)
        analyzer.add_sma(5)
        analyzer.add_sma(20)
        analyzer.add_rsi(14)
        analyzer.add_atr(14)
        analyzer.add_support_resistance(20)
        
        result = analyzer.get_analysis()
        latest = result.iloc[-1]
        prev = result.iloc[-2]
        change = latest['Close'] - prev['Close']
        change_pct = change / prev['Close'] * 100

        # 3. 关键指标
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新价", f"${latest['Close']:.2f}", f"{change_pct:.2f}%")
        c2.metric("RSI (14)", f"{latest['RSI']:.2f}", help=">70超买, <30超卖")
        c3.metric("支撑位", f"${latest['Support_Level']:.2f}")
        c4.metric("阻力位", f"${latest['Resistance_Level']:.2f}")

        # 4. 图表 (简约风格)
        fig = go.Figure()
        
        # K线 (红涨绿跌，符合中国用户习惯，或根据国际惯例调整颜色)
        fig.add_trace(go.Candlestick(
            x=result['Date'],
            open=result['Open'], high=result['High'],
            low=result['Low'], close=result['Close'],
            name='Price',
            increasing_line_color='#ef5350', # 红
            decreasing_line_color='#26a69a'  # 绿
        ))
        
        # 均线
        fig.add_trace(go.Scatter(x=result['Date'], y=result['SMA_5'], line=dict(color='orange', width=1), name='MA5'))
        fig.add_trace(go.Scatter(x=result['Date'], y=result['SMA_20'], line=dict(color='blue', width=1), name='MA20'))
        
        fig.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            height=500,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", y=1.02, x=0),
            template="plotly_white", # 使用白色简约模板
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # 5. AI 顾问
        st.subheader("AI 分析建议")
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        context_str = f"Ticker: {ticker}, Price: {latest['Close']:.2f}, RSI: {latest['RSI']:.2f}, MA5: {latest['SMA_5']:.2f}, Support: {latest['Support_Level']:.2f}"
        user_principles = profile.get_principles_text()
        advisor = LLMAdvisor(api_key=api_key, base_url=base_url, model=model_name)

        if prompt := st.chat_input("输入问题..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_res = ""
                stream = advisor.get_chat_response(st.session_state.messages, context_data=context_str, user_profile=user_principles)
                for chunk in stream:
                    full_res += chunk
                    placeholder.markdown(full_res + "▌")
                placeholder.markdown(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})

    # === Tab 2: 交易终端 (简洁版) ===
    with tab_trading:
        current_mode = st.session_state.trading_mode
        
        try:
            acc = trader.get_account()
        except Exception as e:
            st.error(f"获取账户失败: {e}")
            st.stop()
        
        # 实时计算
        current_prices = {}
        if acc.positions:
            for t in acc.positions.keys():
                if t == ticker:
                    current_prices[t] = latest['Close']
                else:
                    try:
                        d = loader.get_stock_history(t, "1d")
                        if d is not None: current_prices[t] = d.iloc[-1]['Close']
                    except: pass
        
        total_val = acc.total_value(current_prices)
        
        # 资产概览
        c1, c2, c3 = st.columns(3)
        c1.metric("总资产", f"${total_val:,.2f}")
        c2.metric("可用现金", f"${acc.cash:,.2f}")
        c3.metric("持仓市值", f"${total_val - acc.cash:,.2f}")

        st.divider()
        
        # 左右布局：左侧下单，右侧持仓
        col_order, col_pos = st.columns([1, 2])
        
        with col_order:
            st.markdown("#### 下单")
            with st.container(border=True):
                o_ticker = st.text_input("代码", value=ticker).upper()
                o_action = st.radio("方向", ["买入", "卖出"], horizontal=True)
                
                # 获取参考价
                ref_price = latest['Close'] if o_ticker == ticker else 0.0
                
                o_price = st.number_input("价格", value=float(ref_price) if ref_price else 0.0, step=0.1)
                o_qty = st.number_input("数量", value=100, step=100)
                
                if st.button("提交订单", type="primary", use_container_width=True):
                    if "买入" in o_action:
                        ok, msg = trader.buy(o_ticker, o_qty, o_price)
                    else:
                        ok, msg = trader.sell(o_ticker, o_qty, o_price)
                    
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)

        with col_pos:
            st.markdown("#### 持仓明细")
            if acc.positions:
                pos_list = []
                for t, p in acc.positions.items():
                    curr = current_prices.get(t, p['avg_cost'])
                    pnl = (curr - p['avg_cost']) * p['qty']
                    pnl_pct = (curr - p['avg_cost']) / p['avg_cost'] * 100 if p['avg_cost'] > 0 else 0
                    pos_list.append({
                        "代码": t, "数量": p['qty'], "成本": f"{p['avg_cost']:.2f}", 
                        "现价": f"{curr:.2f}", "浮盈": f"{pnl:+.2f} ({pnl_pct:+.2f}%)"
                    })
                st.dataframe(pd.DataFrame(pos_list), use_container_width=True, hide_index=True)
            else:
                st.caption("暂无持仓")

    # === Tab 3: 选股扫描 ===
    with tab_screener:
        c1, c2 = st.columns([4, 1])
        with c1: st.info("扫描美股、港股及A股热门标的，寻找交易机会。")
        with c2: 
            if st.button("开始扫描", use_container_width=True):
                screener = Screener()
                bar = st.progress(0)
                txt = st.empty()
                def prog(c, t, tic):
                    bar.progress(int(c/t*100))
                    txt.caption(f"正在分析: {tic}")
                st.session_state.screener_results = screener.run_screener(prog)
                bar.empty()
                txt.empty()

        if st.session_state.screener_results:
            res = st.session_state.screener_results
            st.subheader("💎 长线潜力")
            if res['long_term']: st.dataframe(pd.DataFrame(res['long_term']), use_container_width=True)
            else: st.write("无")
            
            st.subheader("⚡ 短线机会")
            if res['short_term']: st.dataframe(pd.DataFrame(res['short_term']), use_container_width=True)
            else: st.write("无")

    # === Tab 4: 投资原则 ===
    with tab_philosophy:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("核心纪律")
            st.caption("AI 将基于此提供建议")
            t1 = st.text_area("Principles", value=profile.get_principles_text(), height=300, label_visibility="collapsed", key="p_text")
            if st.button("保存纪律"):
                profile.save_principles(st.session_state.p_text)
                st.success("已保存")
        with c2:
            st.subheader("策略笔记")
            st.caption("记录您的感悟")
            t2 = st.text_area("Notes", value=profile.get_notes(), height=300, label_visibility="collapsed", key="n_text")
            if st.button("保存笔记"):
                profile.save_notes(st.session_state.n_text)
                st.success("已保存")

if __name__ == "__main__":
    main()
