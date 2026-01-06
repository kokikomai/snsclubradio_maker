"""過去の原稿読み込みモジュール"""
from __future__ import annotations

from pathlib import Path

from .config import Config


class ScriptsLoader:
    """過去の原稿を読み込んで分析用データを提供する"""

    def __init__(self, scripts_dir: Path | None = None):
        self.scripts_dir = scripts_dir or Config.SCRIPTS_DIR

    def load_scripts(self) -> list[dict]:
        """過去の原稿を読み込む

        Returns:
            原稿のリスト [{"title": タイトル, "content": 本文, "path": ファイルパス}, ...]
        """
        if not self.scripts_dir.exists():
            raise FileNotFoundError(f"原稿ディレクトリが見つかりません: {self.scripts_dir}")

        scripts = []

        for file_path in self.scripts_dir.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")

                # タイトルをファイル名から抽出（番号,タイトル.md の形式）
                title = file_path.stem
                if "," in title:
                    title = title.split(",", 1)[1].strip()

                scripts.append({
                    "title": title,
                    "content": content,
                    "path": str(file_path),
                })

            except Exception as e:
                # 読み込みエラーは無視して続行
                print(f"Warning: {file_path} の読み込みに失敗: {e}")
                continue

        return scripts

    def get_titles_and_summaries(self, max_content_length: int = 500) -> list[dict]:
        """タイトルと冒頭の要約を取得（スコアリング用）

        Args:
            max_content_length: 本文の最大文字数

        Returns:
            [{"title": タイトル, "summary": 冒頭の要約}, ...]
        """
        scripts = self.load_scripts()

        summaries = []
        for script in scripts:
            # 本文の冒頭部分を取得（見出しや装飾を除去）
            content = script["content"]

            # 画像タグや空行を除去
            lines = []
            for line in content.split("\n"):
                line = line.strip()
                # 画像タグや空行をスキップ
                if not line or line.startswith("![]") or line.startswith("**![]"):
                    continue
                lines.append(line)

            summary = "\n".join(lines[:20])  # 最初の20行
            if len(summary) > max_content_length:
                summary = summary[:max_content_length] + "..."

            summaries.append({
                "title": script["title"],
                "summary": summary,
            })

        return summaries

    def get_all_titles(self) -> list[str]:
        """全ての原稿タイトルを取得"""
        scripts = self.load_scripts()
        return [s["title"] for s in scripts]
