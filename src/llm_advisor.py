import os
from openai import OpenAI

class LLMAdvisor:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "gpt-3.5-turbo"):
        """
        初始化 AI 投资顾问
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.model = model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            print("警告: 未检测到 LLM_API_KEY，AI 分析功能将不可用。")

    def get_analysis(self, ticker: str, price_data: dict, indicators: dict, user_profile: str = "") -> str:
        """
        发送数据给 LLM 获取一次性分析报告
        """
        if not self.client:
            return "AI 顾问未启用 (请配置 API Key)"

        prompt = self._build_prompt(ticker, price_data, indicators)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(user_profile)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI 分析请求失败: {str(e)}"

    def get_chat_response(self, messages: list, context_data: str = "", user_profile: str = "") -> str:
        """
        流式对话接口
        """
        if not self.client:
            yield "请先配置 API Key 才能使用 AI 助手。"
            return

        # 构建包含实时数据的 System Prompt
        system_prompt = f"""你是一位专业的投资交易助手。
当前市场上下文数据如下：
{context_data}

用户的核心投资思想与原则：
{user_profile}

任务：
1. 请结合【最新行情数据】和【最新新闻资讯】（如果有）进行综合分析。
2. 回答要简洁、客观。如果新闻对股价有重大影响（利好/利空），请务必指出。
3. 如果用户问及具体点位，请参考上下文中的支撑/阻力位。
4. 必须遵守用户的投资原则。
"""
        
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                stream=True,
                temperature=0.7
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"对话出错: {str(e)}"

    def _get_system_prompt(self, user_profile: str = ""):
        base_prompt = """你是一位经验丰富的量化交易员和投资顾问。你的目标是帮助用户制定严格、理性的交易计划。
                    
请你根据用户提供的技术指标，输出一份结构化的交易计划。
必须包含明确的数字（价格）和逻辑（理由）。拒绝模棱两可的建议。
"""
        if user_profile:
            base_prompt += f"\n【特别注意】必须遵循以下用户的核心投资原则：\n{user_profile}\n如果市场情况违反这些原则，请明确指出并建议放弃交易。\n"

        base_prompt += """
输出格式要求如下：

### 📊 市场状态分析
(简述当前趋势、强弱状态，以及支撑/阻力位的有效性)

### 🎯 交易计划 (Trading Plan)
| 动作 | 建议价格/区间 | 逻辑理由 |
| :--- | :--- | :--- |
| **买入 (Entry)** | $XXX.XX | (例如：回踩支撑位企稳 / 突破阻力位) |
| **止损 (Stop Loss)** | $XXX.XX | (例如：跌破 ATR 支撑 / 关键均线失效) |
| **止盈 (Take Profit)** | $XXX.XX | (例如：触及上方阻力位 / RSI 超买区域) |

### ⏱️ 时机与策略
(描述最佳的入场时机，例如“等待回调不破”或“立即市价单”。并给出仓位管理建议，如“轻仓试探”或“右侧加仓”)
"""
        return base_prompt

    def _build_prompt(self, ticker: str, price_data: dict, indicators: dict) -> str:
        return f"""
        请分析以下股票数据，并制定具体的交易计划:
        
        【标的】: {ticker}
        
        【最新行情】
        - 当前价格: {price_data.get('current_price', 'N/A')}
        - 日涨跌幅: {price_data.get('change_percent', 'N/A')}%
        
        【关键技术指标】
        - 5日均线 (Trend): {indicators.get('sma_5', 'N/A')}
        - RSI (14) (Momentum): {indicators.get('rsi', 'N/A')}
        - 近期支撑位 (Support): {indicators.get('support', 'N/A')}
        - 近期阻力位 (Resistance): {indicators.get('resistance', 'N/A')}
        - ATR (Volatility): {indicators.get('atr', 'N/A')}
        
        任务：
        1. 判断当前趋势（上涨/下跌/震荡）。
        2. 结合支撑压力位和 ATR，给出具体的【买入价】、【止损价】和【止盈价】。
        3. 如果当前不适合操作，请明确说明“观望”及理由。
        """
