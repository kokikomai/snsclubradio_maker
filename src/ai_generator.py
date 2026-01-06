"""AI生成モジュール（題材提案・原稿作成）"""
import anthropic

from .config import Config


class AIGenerator:
    """Claude APIを使用した題材提案・原稿生成"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    def suggest_topics(self, questions: list[dict], num_topics: int = 5) -> list[dict]:
        """質問リストからラジオ題材を提案する

        Args:
            questions: 質問のリスト [{"row": 行番号, "question": 質問文}, ...]
            num_topics: 提案する題材の数

        Returns:
            題材のリスト [{"title": タイトル, "description": 説明, "related_questions": [質問...]}, ...]
        """
        questions_text = "\n".join(
            [f"- {q['question']}" for q in questions]
        )

        prompt = f"""以下は講座の生徒から寄せられた質問のリストです。
これらの質問を分析して、ラジオ番組で取り上げるべき題材を{num_topics}個提案してください。

【質問リスト】
{questions_text}

【出力形式】
各題材について以下の形式で出力してください：

## 題材1: [タイトル]
**概要**: [この題材で話す内容の概要を2-3文で]
**関連する質問**: [この題材に関連する質問を箇条書きで]
**ポイント**: [リスナーに伝えたい重要なポイント]

---

（以下、題材2〜{num_topics}も同様の形式で）

【注意事項】
- 複数の質問に共通するテーマがあれば、それを1つの題材にまとめてください
- 単独でも重要な質問は独立した題材として提案してください
- リスナーの悩みに寄り添い、実践的なアドバイスができる題材を優先してください
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

        # レスポンスからテキストを抽出
        content = response.content[0].text

        # パース処理（シンプルに題材ごとに分割）
        topics = self._parse_topics(content)

        return topics

    def _parse_topics(self, content: str) -> list[dict]:
        """AIレスポンスから題材をパースする"""
        topics = []
        current_topic = None

        lines = content.split("\n")
        for line in lines:
            line = line.strip()

            # 新しい題材の開始
            if line.startswith("## 題材"):
                if current_topic:
                    topics.append(current_topic)
                # タイトルを抽出
                title = line.split(":", 1)[-1].strip() if ":" in line else line.replace("## 題材", "").strip()
                current_topic = {
                    "title": title,
                    "description": "",
                    "full_text": line + "\n"
                }
            elif current_topic:
                current_topic["full_text"] += line + "\n"
                if line.startswith("**概要**"):
                    current_topic["description"] = line.replace("**概要**:", "").replace("**概要**", "").strip()

        # 最後の題材を追加
        if current_topic:
            topics.append(current_topic)

        return topics

    def generate_script(
        self,
        topic: dict,
        questions: list[dict],
        host_name: str = "パーソナリティ",
        program_name: str = "SNSクラブラジオ",
        duration_minutes: int = 10,
    ) -> str:
        """選択された題材に基づいてラジオ原稿を生成する

        Args:
            topic: 選択された題材
            questions: 元の質問リスト
            host_name: パーソナリティの名前
            program_name: 番組名
            duration_minutes: 目安の放送時間（分）

        Returns:
            ラジオ原稿（テキスト）
        """
        questions_text = "\n".join([f"- {q['question']}" for q in questions])

        prompt = f"""以下の題材と質問をもとに、ラジオ番組の原稿を作成してください。

【番組情報】
- 番組名: {program_name}
- パーソナリティ: {host_name}
- 目安時間: 約{duration_minutes}分

【今回の題材】
{topic.get('full_text', topic.get('title', ''))}

【参考：生徒からの質問】
{questions_text}

【原稿の形式】
以下の構成で原稿を作成してください：

1. **オープニング**（30秒程度）
   - 挨拶と番組紹介
   - 今回のテーマの導入

2. **本編**（{duration_minutes - 2}分程度）
   - 質問の紹介と共感
   - 具体的なアドバイス・解説
   - 実践的なTips
   - 事例や体験談があれば

3. **まとめ・エンディング**（1分程度）
   - 今回のポイントの振り返り
   - リスナーへのメッセージ
   - 次回予告や締めの挨拶

【注意事項】
- 話し言葉で書いてください（「〜ですね」「〜なんですよ」など）
- リスナーに語りかけるような親しみやすいトーンで
- 「（間）」「（笑）」などの演出指示も適宜入れてください
- 質問者の気持ちに寄り添いながら、前向きなアドバイスを
- パーソナリティのセリフは「{host_name}:」で始めてください
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def refine_script(self, script: str, feedback: str) -> str:
        """フィードバックに基づいて原稿を修正する

        Args:
            script: 現在の原稿
            feedback: ユーザーからのフィードバック

        Returns:
            修正された原稿
        """
        prompt = f"""以下のラジオ原稿を、フィードバックに基づいて修正してください。

【現在の原稿】
{script}

【フィードバック】
{feedback}

【注意事項】
- フィードバックの内容を反映しつつ、原稿の良い部分は維持してください
- 全体の流れや長さのバランスに注意してください
- 修正した原稿全体を出力してください
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text
