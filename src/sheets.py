"""Googleスプレッドシート連携モジュール"""
from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import Config


class SheetsClient:
    """Googleスプレッドシートクライアント"""

    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self) -> bool:
        """Google APIに認証する"""
        token_path = Path("token.json")
        credentials_path = Path("credentials.json")

        # 既存のトークンがあれば読み込み
        if token_path.exists():
            self.creds = Credentials.from_authorized_user_file(
                str(token_path), Config.SCOPES
            )

        # 有効な認証情報がない場合
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        "credentials.json が見つかりません。\n"
                        "Google Cloud Console からダウンロードしてプロジェクトルートに配置してください。"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), Config.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # トークンを保存
            with open(token_path, "w") as token:
                token.write(self.creds.to_json())

        self.service = build("sheets", "v4", credentials=self.creds)
        return True

    def get_questions(self, limit: int = 50) -> list[dict]:
        """スプレッドシートから質問を取得する

        Args:
            limit: 取得する最大件数

        Returns:
            質問のリスト [{"row": 行番号, "question": 質問文}, ...]
        """
        if not self.service:
            raise RuntimeError("認証されていません。先にauthenticate()を呼び出してください。")

        try:
            # 列文字を範囲に変換（例: B -> B2:B）
            # 1行目はヘッダーと仮定してスキップ
            range_name = f"{Config.SHEET_NAME}!{Config.QUESTION_COLUMN}2:{Config.QUESTION_COLUMN}"

            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=Config.SPREADSHEET_ID, range=range_name)
                .execute()
            )

            values = result.get("values", [])

            questions = []
            for i, row in enumerate(values[:limit], start=2):
                if row and row[0].strip():  # 空でない行のみ
                    questions.append({"row": i, "question": row[0].strip()})

            return questions

        except HttpError as e:
            raise RuntimeError(f"スプレッドシートの読み取りに失敗しました: {e}")

    def get_all_columns(self, limit: int = 50) -> list[dict]:
        """スプレッドシートから全列のデータを取得する（デバッグ用）

        Returns:
            行データのリスト
        """
        if not self.service:
            raise RuntimeError("認証されていません。")

        try:
            range_name = f"{Config.SHEET_NAME}!A1:Z{limit + 1}"

            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=Config.SPREADSHEET_ID, range=range_name)
                .execute()
            )

            return result.get("values", [])

        except HttpError as e:
            raise RuntimeError(f"スプレッドシートの読み取りに失敗しました: {e}")
