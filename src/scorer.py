"""質問スコアリングモジュール"""
from __future__ import annotations

import json
import re

import anthropic

from .config import Config


class QuestionScorer:
    """AIを使用して質問をスコアリングする"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    def score_questions(
        self,
        questions: list[dict],
        past_titles: list[str],
        past_summaries: list[dict] | None = None,
    ) -> list[dict]:
        """質問をスコアリングして上位を返す

        Args:
            questions: 質問のリスト [{"row": 行番号, "question": 質問文}, ...]
            past_titles: 過去の原稿タイトルのリスト
            past_summaries: 過去の原稿の要約リスト（オプション）

        Returns:
            スコア付き質問のリスト [{"row": 行番号, "question": 質問文, "score": スコア, "reason": 理由}, ...]
        """
        # 過去のタイトルを文字列にまとめる
        past_titles_text = "\n".join([f"- {title}" for title in past_titles])

        # 質問リストを文字列にまとめる
        questions_text = "\n".join(
            [f"{i+1}. {q['question']}" for i, q in enumerate(questions)]
        )

        prompt = f"""あなたはラジオ番組の企画者です。以下の質問リストをスコアリングしてください。

## 過去に扱ったテーマ（タイトル一覧）
{past_titles_text}

## 新しい質問リスト（スコアリング対象）
{questions_text}

## スコアリング基準（各項目10点満点、合計30点満点）

1. **需要スコア（10点）**: 過去に人気があったテーマに関連しているか
   - 過去のテーマと関連性が高い = 需要がある = 高スコア
   - ただし、全く同じテーマは除外（すでに扱い済み）

2. **新鮮さスコア（10点）**: まだ扱っていない新しい角度や切り口か
   - 過去に扱っていない新鮮な内容 = 高スコア
   - すでに詳しく扱ったテーマ = 低スコア

3. **具体性スコア（10点）**: 具体的で答えやすい質問か
   - 具体的な悩みや状況が書かれている = 高スコア
   - 抽象的すぎる質問 = 低スコア
   - リスナーに実践的なアドバイスができる = 高スコア

## 出力形式（JSON）

以下のJSON形式で全ての質問のスコアを出力してください：

```json
[
  {{
    "index": 1,
    "score": 25,
    "demand_score": 8,
    "freshness_score": 9,
    "specificity_score": 8,
    "reason": "スコアの理由を簡潔に"
  }},
  ...
]
```

注意:
- 全ての質問にスコアを付けてください
- indexは質問リストの番号（1から始まる）
- JSONのみを出力し、他の説明は不要です
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )

        # レスポンスからJSONをパース
        content = response.content[0].text
        scores = self._parse_scores(content)

        # 質問データにスコアを追加
        scored_questions = []
        for score_data in scores:
            index = score_data.get("index", 0) - 1  # 0-indexed に変換
            if 0 <= index < len(questions):
                q = questions[index].copy()
                q["score"] = score_data.get("score", 0)
                q["demand_score"] = score_data.get("demand_score", 0)
                q["freshness_score"] = score_data.get("freshness_score", 0)
                q["specificity_score"] = score_data.get("specificity_score", 0)
                q["reason"] = score_data.get("reason", "")
                scored_questions.append(q)

        # スコア順にソート
        scored_questions.sort(key=lambda x: x["score"], reverse=True)

        return scored_questions

    def _parse_scores(self, content: str) -> list[dict]:
        """AIレスポンスからJSONをパース"""
        # JSON部分を抽出
        json_match = re.search(r'\[[\s\S]*\]', content)
        if not json_match:
            return []

        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            # JSONパースに失敗した場合は空リストを返す
            return []

    def get_top_questions(
        self,
        questions: list[dict],
        past_titles: list[str],
        top_n: int | None = None,
    ) -> list[dict]:
        """上位N件の質問を取得

        Args:
            questions: 質問のリスト
            past_titles: 過去の原稿タイトル
            top_n: 取得件数（デフォルト: Config.TOP_QUESTIONS_COUNT）

        Returns:
            上位N件のスコア付き質問リスト
        """
        if top_n is None:
            top_n = Config.TOP_QUESTIONS_COUNT

        scored = self.score_questions(questions, past_titles)
        return scored[:top_n]
