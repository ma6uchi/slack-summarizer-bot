import google.generativeai as genai
import json
import re
import logging
import os # ★ 追加済み

logger = logging.getLogger(__name__)

# グローバル変数としてGeminiモデルのインスタンスを保持
_gemini_model = None
_gemini_model_name = 'gemini-2.0-flash'

# プロンプトファイルのパス
PROMPT_DIR = "prompts"

def _load_prompt(file_name: str) -> str:
    """プロンプトファイルを読み込むヘルパー関数"""
    path = os.path.join(PROMPT_DIR, file_name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"プロンプトファイルが見つかりません: {path}")
        raise
    except Exception as e:
        logger.error(f"プロンプトファイルの読み込みに失敗しました: {path}, Error: {e}")
        raise

def set_gemini_client_and_model(api_key: str, model_name: str = 'gemini-2.0-flash'):
    """
    Geminiクライアントとモデルを設定します。（旧SDK方式）
    """
    global _gemini_model, _gemini_model_name
    _gemini_model_name = model_name

    if api_key:
        try:
            # ★ 修正点 1: genai.configure でAPIキーを設定 ★
            genai.configure(api_key=api_key)

            # ★ 修正点 2: genai.GenerativeModel でモデルを初期化 ★
            _gemini_model = genai.GenerativeModel(_gemini_model_name)

            logger.info(f"Gemini Model '{_gemini_model_name}' が正常に初期化されました。(genai.configure方式)")
        except Exception as e:
            logger.error(f"Gemini Model の初期化に失敗しました: {e}")
            _gemini_model = None
    else:
        _gemini_model = None
        logger.warning("APIキーが提供されていないため、Gemini Modelは初期化されません。")

# --- プロンプト生成関数 (外部ファイル読み込み) ---
def generate_classify_meeting_prompt(text: str) -> str:
    prompt_template = _load_prompt("classify_meeting.txt")
    return prompt_template.format(text=text)

def generate_presales_minutes_prompt(text: str) -> str:
    prompt_template = _load_prompt("presales_minutes.txt")
    return prompt_template.format(text=text)

def generate_requirements_minutes_prompt(text: str) -> str:
    prompt_template = _load_prompt("requirements_minutes.txt")
    return prompt_template.format(text=text)

def generate_maintenance_minutes_prompt(text: str) -> str:
    prompt_template = _load_prompt("maintenance_minutes.txt")
    return prompt_template.format(text=text)

def generate_misc_minutes_prompt(text: str) -> str:
    prompt_template = _load_prompt("misc_minutes.txt")
    return prompt_template.format(text=text)

# --- API呼び出し (変更あり) ---
def _get_gemini_response(prompt: str) -> str:
    """
    Gemini APIにプロンプトを送信し、応答を取得する内部ヘルパー関数。（旧SDK方式）
    """
    if not _gemini_model:
        logger.error("Gemini モデルが初期化されていません。")
        raise Exception("Gemini モデルが初期化されていません。")

    try:
        # ★ 修正点 3: _gemini_model.generate_content を呼び出す ★
        gemini_response = _gemini_model.generate_content(
            contents=prompt
            # generation_config={'temperature': 0.7} # 必要なら調整
        )
        # response.text が空の場合のエラーハンドリングを追加
        if not gemini_response.text:
             logger.warning("Gemini APIからの応答テキストが空です。")
             # 必要であれば、応答オブジェクト全体をログに出力
             logger.debug(f"Gemini full response: {gemini_response}")
             # 安全なデフォルト値を返すか、エラーを発生させる
             # return "(空の応答)"
             raise Exception("Gemini APIからの応答テキストが空でした。")
        return gemini_response.text
    except Exception as e:
        logger.error(f"Gemini API Error: {e}", exc_info=True) # exc_info=Trueでトレースバックを出力
        # エラーの詳細を返すか、より具体的な例外を発生させる
        raise Exception(f"Gemini APIによる処理中にエラーが発生しました: {e}")


def classify_meeting_transcript(text_to_classify: str) -> str:
    """
    Gemini APIを使用して会議の文字起こしを分類します。
    """
    prompt = generate_classify_meeting_prompt(text_to_classify)
    json_str_response = _get_gemini_response(prompt)

    # Geminiの応答にはコードブロックが含まれる場合があるため除去
    cleaned_str = re.sub(r"^```json|```$", "", json_str_response.strip(), flags=re.MULTILINE)
    try:
        classified_data = json.loads(cleaned_str)
        return classified_data.get("category", "その他") # カテゴリを返す
    except json.JSONDecodeError as e:
        logger.error(f"分類結果のJSONパースに失敗しました: {e}. 元の応答: {json_str_response}")
        return "その他" # パース失敗時はデフォルトで「その他」とする

def generate_meeting_minutes(text: str, category: str = "その他") -> str:
    """
    会議の文字起こしから、指定されたカテゴリに基づいて議事録を生成します。
    """
    prompt = ""
    if category == "プリセールス":
        prompt = generate_presales_minutes_prompt(text)
    elif category == "要件定義":
        prompt = generate_requirements_minutes_prompt(text)
    elif category == "運用保守":
        prompt = generate_maintenance_minutes_prompt(text)
    else: # その他または分類失敗時
        prompt = generate_misc_minutes_prompt(text)

    return _get_gemini_response(prompt)

def process_meeting_transcript(plain_text_transcript: str) -> str:
    """
    会議の文字起こしを分類し、その後、分類結果に基づいて議事録を生成します。
    """
    if not _gemini_model: # _gemini_client から _gemini_model に変更
        return "Gemini APIキーが設定されていないか、モデルの初期化に失敗したため、処理できませんでした。"

    try:
        # 1. 会議のカテゴリを分類
        category = classify_meeting_transcript(plain_text_transcript)
        logger.info(f"会議のカテゴリ: {category}")

        # 2. 分類されたカテゴリに基づいて議事録を生成
        minutes_markdown = generate_meeting_minutes(plain_text_transcript, category)
        logger.info("Markdown議事録の生成が完了しました。")
        return minutes_markdown

    except Exception as e:
        logger.error(f"会議文字起こし処理全体でエラーが発生しました: {e}", exc_info=True)
        # ユーザーに返すエラーメッセージはシンプルに
        return f"議事録の生成中にエラーが発生しました。詳細はログを確認してください。"