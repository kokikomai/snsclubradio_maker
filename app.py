"""SNSクラブラジオ原稿作成ツール - Webアプリ"""
import streamlit as st
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.sheets import SheetsClient
from src.ai_generator import AIGenerator
from src.scripts_loader import ScriptsLoader
from src.scorer import QuestionScorer

# ページ設定
st.set_page_config(
    page_title="SNSクラブラジオ 原稿作成ツール",
    page_icon="🎙️",
    layout="wide",
)

# セッション状態の初期化
if "step" not in st.session_state:
    st.session_state.step = 1
if "questions" not in st.session_state:
    st.session_state.questions = []
if "top_questions" not in st.session_state:
    st.session_state.top_questions = []
if "topics" not in st.session_state:
    st.session_state.topics = []
if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = None
if "script" not in st.session_state:
    st.session_state.script = ""
if "past_titles" not in st.session_state:
    st.session_state.past_titles = []


def reset_state():
    """状態をリセット"""
    st.session_state.step = 1
    st.session_state.questions = []
    st.session_state.top_questions = []
    st.session_state.topics = []
    st.session_state.selected_topic = None
    st.session_state.script = ""


def main():
    st.title("🎙️ SNSクラブラジオ 原稿作成ツール")
    st.markdown("生徒の質問をスコアリングし、原稿を自動生成します")

    # サイドバー：進行状況
    with st.sidebar:
        st.header("📋 進行状況")
        steps = [
            "1. 過去原稿の読み込み",
            "2. 質問の取得",
            "3. スコアリング",
            "4. 題材の提案",
            "5. 題材の選択",
            "6. 原稿の生成",
        ]
        for i, step in enumerate(steps, 1):
            if i < st.session_state.step:
                st.markdown(f"✅ {step}")
            elif i == st.session_state.step:
                st.markdown(f"👉 **{step}**")
            else:
                st.markdown(f"⬜ {step}")

        st.divider()
        if st.button("🔄 最初からやり直す"):
            reset_state()
            st.rerun()

    # 設定検証
    errors = Config.validate()
    if errors:
        st.error("設定エラー")
        for error in errors:
            st.warning(error)
        st.info("`.env` ファイルを確認してください")
        return

    # Step 1: 過去原稿の読み込み
    if st.session_state.step == 1:
        st.header("Step 1: 過去原稿の読み込み")

        if st.button("📚 過去原稿を読み込む", type="primary"):
            with st.spinner("原稿ファイルを読み込み中..."):
                try:
                    loader = ScriptsLoader()
                    st.session_state.past_titles = loader.get_all_titles()
                    st.success(f"✅ {len(st.session_state.past_titles)}本の過去原稿を読み込みました")
                    st.session_state.step = 2
                    st.rerun()
                except FileNotFoundError as e:
                    st.error(f"エラー: {e}")
                    st.info("SCRIPTS_DIR の設定を確認してください")

    # Step 2: 質問の取得
    elif st.session_state.step == 2:
        st.header("Step 2: 質問の取得")
        st.info(f"📊 スプレッドシート: {Config.SHEET_NAME} / {Config.QUESTION_COLUMN}列")

        if st.button("📥 スプレッドシートから質問を取得", type="primary"):
            with st.spinner("Googleスプレッドシートに接続中..."):
                try:
                    sheets_client = SheetsClient()
                    sheets_client.authenticate()
                    st.session_state.questions = sheets_client.get_questions(limit=100)

                    if st.session_state.questions:
                        st.success(f"✅ {len(st.session_state.questions)}件の質問を取得しました")
                        st.session_state.step = 3
                        st.rerun()
                    else:
                        st.warning("質問が見つかりませんでした")
                except Exception as e:
                    st.error(f"エラー: {e}")

    # Step 3: スコアリング
    elif st.session_state.step == 3:
        st.header("Step 3: 質問のスコアリング")
        st.info(f"📝 {len(st.session_state.questions)}件の質問をAIがスコアリングします")

        col1, col2 = st.columns(2)
        with col1:
            top_n = st.number_input("上位何件を選出？", min_value=5, max_value=20, value=10)

        if st.button("🔍 スコアリング開始", type="primary"):
            with st.spinner("AIが質問を分析中...（少し時間がかかります）"):
                try:
                    scorer = QuestionScorer()
                    st.session_state.top_questions = scorer.get_top_questions(
                        st.session_state.questions,
                        st.session_state.past_titles,
                        top_n=top_n,
                    )
                    st.session_state.step = 4
                    st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")

    # Step 4: 題材の提案
    elif st.session_state.step == 4:
        st.header("Step 4: 題材の提案")

        # スコアリング結果を表示
        st.subheader("📊 スコアリング結果（上位質問）")

        for i, q in enumerate(st.session_state.top_questions, 1):
            with st.expander(f"#{i} スコア: {q.get('score', 0)}点 - {q['question'][:50]}..."):
                st.markdown(f"**質問:** {q['question']}")
                col1, col2, col3 = st.columns(3)
                col1.metric("需要", f"{q.get('demand_score', 0)}/10")
                col2.metric("新鮮さ", f"{q.get('freshness_score', 0)}/10")
                col3.metric("具体性", f"{q.get('specificity_score', 0)}/10")
                st.markdown(f"**評価理由:** {q.get('reason', '')}")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            num_topics = st.number_input("提案する題材の数", min_value=3, max_value=10, value=5)

        if st.button("💡 題材を提案", type="primary"):
            with st.spinner("AIが題材を分析中..."):
                try:
                    ai_generator = AIGenerator()
                    st.session_state.topics = ai_generator.suggest_topics(
                        st.session_state.top_questions,
                        num_topics=num_topics,
                    )
                    st.session_state.step = 5
                    st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")

    # Step 5: 題材の選択
    elif st.session_state.step == 5:
        st.header("Step 5: 題材の選択")

        for i, topic in enumerate(st.session_state.topics):
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.subheader(f"題材 {i+1}: {topic['title']}")
                    st.markdown(topic.get("full_text", "")[:500] + "..." if len(topic.get("full_text", "")) > 500 else topic.get("full_text", ""))
                with col2:
                    if st.button(f"✅ 選択", key=f"select_{i}"):
                        st.session_state.selected_topic = topic
                        st.session_state.step = 6
                        st.rerun()
                st.divider()

    # Step 6: 原稿の生成
    elif st.session_state.step == 6:
        st.header("Step 6: 原稿の生成")

        st.success(f"選択した題材: **{st.session_state.selected_topic['title']}**")

        col1, col2, col3 = st.columns(3)
        with col1:
            host_name = st.text_input("パーソナリティ名", value="駒居")
        with col2:
            program_name = st.text_input("番組名", value="SNSクラブラジオ")
        with col3:
            duration = st.number_input("目安時間（分）", min_value=5, max_value=30, value=10)

        if not st.session_state.script:
            if st.button("📝 原稿を生成", type="primary"):
                with st.spinner("AIが原稿を作成中...（少し時間がかかります）"):
                    try:
                        ai_generator = AIGenerator()
                        st.session_state.script = ai_generator.generate_script(
                            topic=st.session_state.selected_topic,
                            questions=st.session_state.top_questions,
                            host_name=host_name,
                            program_name=program_name,
                            duration_minutes=duration,
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラー: {e}")

        if st.session_state.script:
            st.subheader("📄 生成された原稿")
            st.markdown(st.session_state.script)

            st.divider()

            # 修正機能
            st.subheader("✏️ 原稿の修正")
            feedback = st.text_area("修正内容を入力", placeholder="例: もっとカジュアルな口調にしてください")
            if st.button("🔄 修正を反映"):
                if feedback:
                    with st.spinner("原稿を修正中..."):
                        try:
                            ai_generator = AIGenerator()
                            st.session_state.script = ai_generator.refine_script(
                                st.session_state.script,
                                feedback,
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"エラー: {e}")

            st.divider()

            # 保存機能
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 ファイルに保存"):
                    output_dir = Config.ensure_output_dir()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = output_dir / f"script_{timestamp}.md"

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(st.session_state.script)

                    st.success(f"保存しました: {output_path}")

            with col2:
                st.download_button(
                    label="📥 ダウンロード",
                    data=st.session_state.script,
                    file_name=f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                )


if __name__ == "__main__":
    main()
