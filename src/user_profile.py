import json
import os

class UserProfile:
    def __init__(self, filepath: str = "user_profile.json"):
        self.filepath = filepath
        self.data = self._load_data()

    def _load_data(self) -> dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self._default_profile()
        return self._default_profile()

    def _default_profile(self) -> dict:
        return {
            "principles": [
                "永远顺势而为，不逆势抄底",
                "单笔交易亏损控制在总资金的 2% 以内",
                "看不懂的行情就空仓"
            ],
            "strategy_notes": "偏好右侧突破交易，关注成交量配合。"
        }

    def save_principles(self, principles: str):
        """
        保存用户输入的原则文本 (按行分割)
        """
        # 将多行文本转换为列表，过滤空行
        p_list = [p.strip() for p in principles.split('\n') if p.strip()]
        self.data["principles"] = p_list
        self._save()

    def save_notes(self, notes: str):
        self.data["strategy_notes"] = notes
        self._save()

    def get_principles_text(self) -> str:
        return "\n".join(self.data.get("principles", []))

    def get_notes(self) -> str:
        return self.data.get("strategy_notes", "")

    def _save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

