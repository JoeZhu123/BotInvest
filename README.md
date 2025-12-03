# BotInvest - 智能投资交易助理

BotInvest 是一个基于 Python 和 LLM (大语言模型) 的智能投资辅助系统。它不仅是一个行情分析工具，更是一个能够理解你投资哲学、帮你执行交易纪律、并支持模拟交易的私人投资顾问。

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-ff4b4b)
![OpenAI/DeepSeek](https://img.shields.io/badge/AI-Powered-green)

## 🚀 核心功能

### 1. 🤖 AI 智能交易顾问 (Interactive Advisor)
- **自然语言对话**: 像聊天一样询问 "AAPL 现在能买吗？"，AI 会基于实时数据回答。
- **专业交易计划**: 每次分析都会生成结构化的交易计划，包含 **买入点 (Entry)**、**止损点 (Stop Loss)** 和 **止盈点 (Take Profit)**。
- **数据驱动**: 结合 RSI、均线 (SMA)、ATR (波动率) 和 支撑/阻力位 进行客观分析。

### 2. 📅 智能选股推荐 (Smart Screener)
- **自动扫描**: 一键扫描美股 (如 AAPL, TSLA) 和 港股 (如 腾讯, 阿里) 的热门标的。
- **机会分类**:
    - **💎 长期持有**: 筛选趋势向上且估值合理的稳健标的。
    - **⚡ 短期交易**: 筛选超卖反弹或均线突破的短线机会。

### 3. 💸 实盘/模拟交易 (Trading Desk)
- **本地模拟**: 内置 Paper Trader，默认提供 $100,000 模拟资金。
- **账户管理**: 实时计算持仓市值、浮动盈亏，支持买入/卖出操作。
- **数据持久化**: 交易记录和持仓自动保存在 `portfolio.json`，重启不丢失。
- **可扩展架构**: 代码采用适配器模式，支持未来接入富途 (Futu) 或 盈透 (IB) 实盘 API。

### 4. 📝 投资思想库 (Philosophy & Discipline)
- **个性化记忆**: 记录你的核心投资原则（如 "不追高"、"亏损不过 2%"）。
- **纪律执行**: AI 在给出建议时，会**强制检查**是否违背了你的原则，并发出警告。

---

## 🛠️ 快速开始

### 1. 环境准备

确保已安装 Python 3.9 或更高版本。

```bash
# 克隆项目或下载源码
git clone https://github.com/your-repo/BotInvest.git
cd BotInvest

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 AI (可选但推荐)

为了使用 AI 聊天功能，你需要配置 OpenAI 或 DeepSeek 的 API Key。
你可以直接在网页界面中输入，或者在运行前设置环境变量：

```powershell
# PowerShell
$env:LLM_API_KEY = "你的_sk_key"
# 如果使用 DeepSeek:
$env:LLM_BASE_URL = "https://api.deepseek.com/v1"
$env:LLM_MODEL = "deepseek-chat"
```

### 3. 启动应用

```bash
python -m streamlit run src/app.py
```

浏览器会自动打开 `http://localhost:8501`。

---

## 💡 完整投资闭环

BotInvest 旨在打造一个完整的投资工作流：

1.  **发现 (Discovery)**: 
    - 进入 **"智能选股推荐"** Tab，点击扫描。
    - 从推荐列表中找到感兴趣的标的（例如 `TSLA`）。

2.  **分析 (Analysis)**:
    - 切换到 **"市场分析"** Tab，输入 `TSLA`。
    - 查看 K 线图和指标。
    - 询问 AI: "基于我的原则，现在适合买入 TSLA 吗？"

3.  **执行 (Execution)**:
    - 如果 AI 建议买入，切换到 **"实盘/模拟交易"** Tab。
    - 输入代码、价格和数量，点击 **"提交订单"**。

4.  **复盘 (Review)**:
    - 在 **"我的投资思想"** Tab 中记录本次交易的感悟，不断完善自己的投资体系。

---

## 📂 项目结构

```text
BotInvest/
├── data/               # 本地数据存储 (缓存/模拟数据)
├── src/                # 源代码目录
│   ├── app.py          # Web 应用入口 (Streamlit)
│   ├── trading_system.py # 交易系统 (PaperTrader)
│   ├── screener.py     # 选股器逻辑
│   ├── llm_advisor.py  # AI 顾问核心
│   ├── data_loader.py  # 数据获取模块
│   ├── analysis.py     # 技术分析引擎
│   └── user_profile.py # 用户档案管理
├── portfolio.json      # 模拟交易账户数据 (自动生成)
├── user_profile.json   # 用户投资原则存档 (自动生成)
└── requirements.txt    # 依赖列表
```

## ⚠️ 免责声明

本工具仅供学习和辅助分析使用，不构成任何投资建议。股市有风险，投资需谨慎。AI 生成的内容可能存在幻觉，请务必结合自身判断。
