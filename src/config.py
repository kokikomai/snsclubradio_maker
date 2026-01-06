"""設定管理モジュール"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Config:
    """アプリケーション設定"""

    # Anthropic API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Google Spreadsheet
    SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
    SHEET_NAME: str = os.getenv("SHEET_NAME", "質問")
    QUESTION_COLUMN: str = os.getenv("QUESTION_COLUMN", "B")

    # 出力設定
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "output"))

    # 過去の原稿ディレクトリ
    SCRIPTS_DIR: Path = Path(os.getenv("SCRIPTS_DIR", "/home/user/SnsClub-radio/past drafts"))

    # スコアリング設定
    TOP_QUESTIONS_COUNT: int = int(os.getenv("TOP_QUESTIONS_COUNT", "10"))

    # Google OAuth スコープ
    SCOPES: list[str] = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    @classmethod
    def validate(cls) -> list[str]:
        """設定の検証。エラーがあればリストで返す"""
        errors = []

        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY が設定されていません")

        if not cls.SPREADSHEET_ID:
            errors.append("SPREADSHEET_ID が設定されていません")

        return errors

    @classmethod
    def ensure_output_dir(cls) -> Path:
        """出力ディレクトリを作成して返す"""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return cls.OUTPUT_DIR
