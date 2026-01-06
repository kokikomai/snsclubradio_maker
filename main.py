#!/usr/bin/env python3
"""SNSクラブラジオ原稿作成ツール"""
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.markdown import Markdown
from rich.table import Table

from src.config import Config
from src.sheets import SheetsClient
from src.ai_generator import AIGenerator

console = Console()


def print_header():
    """ヘッダーを表示"""
    console.print(
        Panel.fit(
            "[bold blue]SNSクラブラジオ 原稿作成ツール[/bold blue]\n"
            "[dim]生徒の質問から題材を提案し、原稿を自動生成します[/dim]",
            border_style="blue",
        )
    )
    console.print()


def validate_config() -> bool:
    """設定を検証"""
    errors = Config.validate()
    if errors:
        console.print("[bold red]設定エラー:[/bold red]")
        for error in errors:
            console.print(f"  - {error}")
        console.print("\n[dim].env ファイルを確認してください[/dim]")
        return False
    return True


def fetch_questions(sheets_client: SheetsClient) -> list[dict]:
    """スプレッドシートから質問を取得"""
    console.print("[bold]1. 質問を取得中...[/bold]")

    with console.status("[bold green]Googleスプレッドシートに接続中..."):
        sheets_client.authenticate()

    with console.status("[bold green]質問を読み込み中..."):
        questions = sheets_client.get_questions(limit=50)

    if not questions:
        console.print("[yellow]質問が見つかりませんでした。[/yellow]")
        console.print(f"[dim]シート名: {Config.SHEET_NAME}, 列: {Config.QUESTION_COLUMN}[/dim]")
        return []

    # 質問一覧を表示
    table = Table(title=f"取得した質問 ({len(questions)}件)")
    table.add_column("No.", style="dim", width=4)
    table.add_column("質問内容")

    for i, q in enumerate(questions, 1):
        # 長い質問は省略
        question_text = q["question"]
        if len(question_text) > 80:
            question_text = question_text[:77] + "..."
        table.add_row(str(i), question_text)

    console.print(table)
    console.print()

    return questions


def suggest_topics(ai_generator: AIGenerator, questions: list[dict]) -> list[dict]:
    """題材を提案"""
    console.print("[bold]2. 題材を提案中...[/bold]")

    num_topics = IntPrompt.ask(
        "提案する題材の数",
        default=5,
        show_default=True,
    )

    with console.status("[bold green]AIが題材を分析中..."):
        topics = ai_generator.suggest_topics(questions, num_topics=num_topics)

    if not topics:
        console.print("[yellow]題材の提案に失敗しました。[/yellow]")
        return []

    # 題材一覧を表示
    console.print()
    console.print("[bold green]提案された題材:[/bold green]")
    console.print()

    for i, topic in enumerate(topics, 1):
        console.print(
            Panel(
                f"[bold]{topic['title']}[/bold]\n\n"
                f"{topic.get('description', '')}\n\n"
                f"[dim]{topic.get('full_text', '')[:500]}...[/dim]"
                if len(topic.get("full_text", "")) > 500
                else f"[bold]{topic['title']}[/bold]\n\n{topic.get('full_text', '')}",
                title=f"[bold cyan]題材 {i}[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print()

    return topics


def select_topic(topics: list[dict]) -> dict | None:
    """題材を選択"""
    console.print("[bold]3. 題材を選択してください[/bold]")

    while True:
        choice = Prompt.ask(
            f"題材番号を入力 (1-{len(topics)}) または 'q' で終了",
            default="1",
        )

        if choice.lower() == "q":
            return None

        try:
            index = int(choice) - 1
            if 0 <= index < len(topics):
                selected = topics[index]
                console.print(f"\n[bold green]選択: {selected['title']}[/bold green]\n")
                return selected
            else:
                console.print("[red]無効な番号です。[/red]")
        except ValueError:
            console.print("[red]数字を入力してください。[/red]")


def generate_script(
    ai_generator: AIGenerator,
    topic: dict,
    questions: list[dict],
) -> str:
    """原稿を生成"""
    console.print("[bold]4. 原稿を生成中...[/bold]")

    # オプション設定
    host_name = Prompt.ask("パーソナリティ名", default="パーソナリティ")
    program_name = Prompt.ask("番組名", default="SNSクラブラジオ")
    duration = IntPrompt.ask("目安時間（分）", default=10)

    with console.status("[bold green]AIが原稿を作成中...（少し時間がかかります）"):
        script = ai_generator.generate_script(
            topic=topic,
            questions=questions,
            host_name=host_name,
            program_name=program_name,
            duration_minutes=duration,
        )

    return script


def display_and_save_script(script: str) -> Path | None:
    """原稿を表示して保存"""
    console.print()
    console.print("[bold]5. 生成された原稿[/bold]")
    console.print()

    # Markdownとして表示
    console.print(Panel(Markdown(script), title="原稿", border_style="green"))

    # 保存確認
    if Confirm.ask("\n原稿をファイルに保存しますか？", default=True):
        output_dir = Config.ensure_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"script_{timestamp}.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script)

        console.print(f"[bold green]保存しました: {output_path}[/bold green]")
        return output_path

    return None


def refine_script_loop(ai_generator: AIGenerator, script: str) -> str:
    """原稿の修正ループ"""
    current_script = script

    while True:
        if not Confirm.ask("\n原稿を修正しますか？", default=False):
            break

        feedback = Prompt.ask("修正内容を入力してください")

        with console.status("[bold green]原稿を修正中..."):
            current_script = ai_generator.refine_script(current_script, feedback)

        console.print()
        console.print(Panel(Markdown(current_script), title="修正後の原稿", border_style="green"))

    return current_script


def main():
    """メイン処理"""
    print_header()

    # 設定検証
    if not validate_config():
        sys.exit(1)

    try:
        # 初期化
        sheets_client = SheetsClient()
        ai_generator = AIGenerator()

        # 1. 質問取得
        questions = fetch_questions(sheets_client)
        if not questions:
            sys.exit(1)

        # 2. 題材提案
        topics = suggest_topics(ai_generator, questions)
        if not topics:
            sys.exit(1)

        # 3. 題材選択
        selected_topic = select_topic(topics)
        if not selected_topic:
            console.print("[yellow]終了します。[/yellow]")
            sys.exit(0)

        # 4. 原稿生成
        script = generate_script(ai_generator, selected_topic, questions)

        # 5. 表示・保存
        display_and_save_script(script)

        # 6. 修正ループ
        final_script = refine_script_loop(ai_generator, script)

        # 最終保存
        if final_script != script:
            if Confirm.ask("\n最終版を保存しますか？", default=True):
                output_dir = Config.ensure_output_dir()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = output_dir / f"script_final_{timestamp}.md"

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_script)

                console.print(f"[bold green]保存しました: {output_path}[/bold green]")

        console.print("\n[bold blue]お疲れさまでした！[/bold blue]")

    except FileNotFoundError as e:
        console.print(f"[bold red]エラー: {e}[/bold red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]中断しました。[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]予期しないエラー: {e}[/bold red]")
        raise


if __name__ == "__main__":
    main()
