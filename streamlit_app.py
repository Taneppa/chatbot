import streamlit as st
from google import genai
from google.genai import types

# アプリのタイトルと説明
st.title("💬 Gemini Chatbot (with Web Search)")
st.write(
    "GoogleのGeminiモデルを利用したチャットボットです。"
    "Google検索機能が有効になっており、最新の情報に基づいた回答が可能です。"
)

# SecretsからAPIキーを安全に取得（画面の入力欄は廃止）
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("APIキーが設定されていません。StreamlitのSecrets設定を確認してください。")
    st.stop() # キーがない場合はここで処理を停止

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

    # Gemini APIを呼び出し、ストリーミングで応答を生成
    # （最新モデル gemini-3.8-flash を指定し、Google検索ツールを有効化）
    response_stream = client.models.generate_content_stream(
        model="gemini-3.8-flash",
        contents=formatted_contents,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    # st.write_streamでチャンクを逐次処理するためのジェネレータ関数
    def stream_generator():
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    # ストリーミング応答をUIに表示し、完了後に履歴に保存
    with st.chat_message("assistant"):
        response = st.write_stream(stream_generator)
    st.session_state.messages.
