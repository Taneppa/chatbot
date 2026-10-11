import time
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

    # Gemini API用の履歴フォーマットに変換 (Streamlitの'assistant'をGeminiの'model'に変換)
    formatted_contents = []
    for m in st.session_state.messages:
        role = "user" if m["role"] == "user" else "model"
        formatted_contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=m["content"])]
            )
        )

    # 503(サーバー過負荷)・429(レート制限) エラー対策付きストリーム生成関数
    def stream_generator():
        max_retries = 3
        delay = 2  # 初回待機時間（秒）

        for attempt in range(max_retries):
            try:
                response_stream = client.models.generate_content_stream(
                    model="gemini-3.8-flash",
                    contents=formatted_contents,
                )
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return  # 正常応答が終わったら処理完了

            except errors.APIError as e:
                err_str = str(e)
                # 503 (サーバー混雑) の場合は時間を置いて自動リトライ
                if "503" in err_str:
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2  # 待機時間を段階的に増やす (2秒 -> 4秒)
                        continue
                    else:
                        yield "⚠️ Googleのサーバーが現在高負荷状態です（503エラー）。1〜2分ほど時間を置いてから再度お試しください。"
                        return
                # 429 (利用制限超過) の場合
                elif "429" in err_str:
                    yield "⚠️ APIの利用制限（429 Quota Exceeded）に達しました。1分ほど時間を置いてお試しください。"
                    return
                else:
                    yield f"**APIエラーが発生しました:** {e}"
                    return
            except Exception as e:
                yield f"**予期せぬエラーが発生しました:** {e}"
                return

    # ストリーミング応答をUIに表示し、完了後に履歴に保存
    with st.chat_message("assistant"):
        response = st.write_stream(stream_generator)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
