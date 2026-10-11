import streamlit as st
from google import genai
from google.genai import types
from google.genai import errors

# アプリのタイトルと説明
st.title("💬 Gemini Chatbot")
st.write("GoogleのGeminiモデルを利用したチャットボットです。")

# SecretsからAPIキーを安全に取得
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("APIキーが設定されていません。StreamlitのSecrets設定を確認してください。")
    st.stop()

# Geminiクライアントの初期化
client = genai.Client(api_key=gemini_api_key)

# チャット履歴を保持するセッションステートの初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# 既存のチャット履歴を画面に表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーからのメッセージ入力
if prompt := st.chat_input("何でも聞いてください"):

    # ユーザーの入力を履歴に追加し、画面に表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gemini API用の履歴フォーマットに変換
    formatted_contents = []
    for m in st.session_state.messages:
        role = "user" if m["role"] == "user" else "model"
        formatted_contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=m["content"])]
            )
        )

    # ストリーム生成関数
    def stream_generator():
        try:
            # 429回避のためGoogle検索ツールは外し、標準モデル呼び出しに変更
            response_stream = client.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=formatted_contents,
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

        except errors.ClientError as e:
            if "429" in str(e):
                yield (
                    "⚠️ **APIの利用制限（429 Quota Exceeded）に達しました。**\n\n"
                    "数分待ってから再度送信してください。無料枠の1分間あたりのリクエスト上限を超えています。"
                )
            else:
                yield f"**エラーが発生しました:** {e}"
        except Exception as e:
            yield f"**予期せぬエラーが発生しました:** {e}"

    # ストリーミング応答をUIに表示し、完了後に履歴に保存
    with st.chat_message("assistant"):
        response = st.write_stream(stream_generator)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
