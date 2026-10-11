import streamlit as st
from google import genai
from google.genai import types
from google.genai import errors
import time

# アプリのタイトルと説明
st.title("💬 Gemini Chatbot")
st.write(
    "GoogleのGemini 3.8 Flashを利用したチャットボットです。"
    "Google検索機能が有効になっており、最新の情報に基づいた回答が可能です。"
)

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

    # 503エラー(サーバー高負荷)対策用のリトライ処理付きストリームジェネレータ
    def stream_generator():
        retries = 3
        delay = 2

        for attempt in range(retries):
            try:
                # API呼び出し
                response_stream = client.models.generate_content_stream(
                    model="gemini-3.8-flash",  # 正しい最新モデル
                    contents=formatted_contents,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                
                # チャンクをストリーミング
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return  # 成功したらループを抜ける

            except errors.ClientError as e:
                # 503 (Service Unavailable) や 429 (Too Many Requests) の場合のみリトライ
                error_msg = str(e)
                if "503" in error_msg or "429" in error_msg:
                    if attempt < retries - 1:
                        yield f"*(サーバー高負荷のため {delay}秒後に再試行します...)*\n\n"
                        time.sleep(delay)
                        delay *= 2  # エクスポネンシャルバックオフ (2秒, 4秒, 8秒...)
                        continue
                
                # それ以外のエラー、またはリトライ上限に達した場合はエラーを表示
                yield f"**エラーが発生しました:** {error_msg}"
                return
            except Exception as e:
                yield f"**予期せぬエラーが発生しました:** {str(e)}"
                return

    # ストリーミング応答をUIに表示し、完了後に履歴に保存
    with st.chat_message("assistant"):
        response = st.write_stream(stream_generator)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
