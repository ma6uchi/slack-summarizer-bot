import google.generativeai as genai

_gemini_model = None

def set_gemini_model(model_name_or_object):
    """
    Geminiモデルを設定します。lambda_function.pyから呼び出されます。
    """
    global _gemini_model
    if model_name_or_object:
        if isinstance(model_name_or_object, str):
            _gemini_model = genai.GenerativeModel(model_name_or_object)
        else:
            _gemini_model = model_name_or_object
    else:
        _gemini_model = None

def get_summary_from_gemini(text_to_summarize):
    """
    Gemini APIを使用してテキストを要約します。
    """
    if not _gemini_model:
        return "Gemini APIキーが設定されていないため、要約できませんでした。"

    try:
        prompt = f"以下のテキストを要約してください。重要なポイントを抽出し、簡潔にまとめてください。\n\nテキスト:\n{text_to_summarize}"
        gemini_response = _gemini_model.generate_content(prompt)
        print("Gemini APIによる要約が完了しました。")
        return gemini_response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"Gemini APIによる要約中にエラーが発生しました: {e}"