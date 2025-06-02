from google import genai

# グローバル変数としてGeminiクライアントのインスタンスを保持
_gemini_client = None
_gemini_model_name = 'gemini-2.0-flash' # 使用するGeminiモデル名をデフォルトとして設定

def set_gemini_client_and_model(api_key: str, model_name: str = 'gemini-2.0-flash'):
    """
    Geminiクライアントとモデルを設定します。
    この関数は、lambda_function.pyからAPIキーを渡して呼び出されることを想定しています。
    """
    global _gemini_client, _gemini_model_name
    _gemini_model_name = model_name

    if api_key:
        try:
            _gemini_client = genai.Client(api_key=api_key)
            print("Gemini Client が正常に初期化されました。")
        except Exception as e:
            print(f"Gemini Client の初期化に失敗しました: {e}")
            _gemini_client = None
    else:
        _gemini_client = None
        print("APIキーが提供されていないため、Gemini Clientは初期化されません。")

def get_summary_from_gemini(text_to_summarize: str) -> str:
    """
    Gemini APIを使用してテキストを要約します。
    """
    if not _gemini_client:
        return "Gemini APIキーが設定されていないか、クライアントの初期化に失敗したため、要約できませんでした。"

    try:
        prompt = f"以下のテキストを要約してください。重要なポイントを抽出し、簡潔にまとめてください。\n\nテキスト:\n{text_to_summarize}"
        
        # _gemini_client を通じて models コレクションにアクセスし、generate_content を呼び出す
        gemini_response = _gemini_client.models.generate_content(
            model=_gemini_model_name,
            contents=prompt
        )
        print("Gemini APIによる要約が完了しました。")
        return gemini_response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"Gemini APIによる要約中にエラーが発生しました: {e}"