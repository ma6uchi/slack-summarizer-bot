from google import genai
import json
import re

# グローバル変数としてGeminiクライアントのインスタンスを保持
_gemini_client = None
# デフォルトモデルをgemini-2.0-flashに設定 (速度とコスト効率を考慮)
_gemini_model_name = 'gemini-2.0-flash'

def set_gemini_client_and_model(api_key: str, model_name: str = 'gemini-2.0-flash'):
    """
    Geminiクライアントとモデルを設定します。
    この関数は、lambda_function.pyからAPIキーを渡して呼び出されることを想定しています。
    """
    global _gemini_client, _gemini_model_name
    _gemini_model_name = model_name

    if api_key:
        try:
            # genai.Client を使用 (genai.configure は不要)
            _gemini_client = genai.Client(api_key=api_key)
            print("Gemini Client が正常に初期化されました。")
        except Exception as e:
            print(f"Gemini Client の初期化に失敗しました: {e}")
            _gemini_client = None
    else:
        _gemini_client = None
        print("APIキーが提供されていないため、Gemini Clientは初期化されません。")

# --- 会議の分類プロンプト ---
def generate_classify_meeting_prompt(text: str) -> str:
    prompt = f"""
あなたは会議の文字起こしを、次の4つのカテゴリのいずれかに分類するAIです。
以下の定義を参考に、与えられた会話の内容を「最も適切な1つのカテゴリ」に分類してください。

【カテゴリと定義】
1. プリセールス: 提案・見積・商談・ヒアリングなどの受注前活動
2. 要件定義: 受注後の要件確認・仕様設計に関する話
3. 運用保守: リリース後のサポート・障害・問い合わせ対応
4. その他: 雑談やカテゴリ外の話題（社内連絡、採用など）

【出力形式】
{{
  "category": "プリセールス" または "要件定義" または "運用保守" または "その他",
  "reason": "その分類を選んだ理由（根拠となるキーワードや文脈）"
}}

【会議の文字起こし】
{text}
"""
    return prompt

# --- 会議カテゴリ別の議事録生成プロンプト ---
def generate_presales_minutes_prompt(text: str) -> str:
    return f"""
以下はプリセールスフェーズの会議の不完全な文字起こしです。

あなたの仕事は、次のMarkdownテンプレートの形式に沿って、議事録を構成することです。
**テンプレート構造や見出しを変更せずに、各セクションに適切な内容を記入してください。**
---

## 会議概要
- 会議の目的: 商談に向けた準備、提案内容の整理
- 参加者: 不明

## 顧客の要望・課題
- （顧客の現在の課題や背景を箇条書きで記載）

## 提案内容と議論
- （提案の骨子、代替案、質疑応答などの概要を記載）

## 次のアクション
- （誰が、何を、いつまでに、を箇条書きで明確に）

---

以下が会議の文字起こしです：

{text}

以上のテンプレートに基づいて、Markdown議事録を作成してください。
"""

def generate_requirements_minutes_prompt(text: str) -> str:
    return f"""
以下は要件定義フェーズの会議の不完全な文字起こしです。

あなたの仕事は、以下のMarkdownテンプレートに従って、議事録を構成することです。
**テンプレートの構造や見出しは絶対に変更せず、各セクションに適切な内容を記入してください。**

---

## 会議概要
- 会議の目的: システム要件の定義・調整
- 参加者: 不明

## 議論された要件
- 機能要件: （例：検索機能、登録画面など。複数ある場合は箇条書き）
- 非機能要件: （例：性能要件、セキュリティ、運用体制など）

## 合意事項
- （今回の会議で確定した仕様・決定事項を箇条書き）

## 未決事項・懸念点
- （保留された話題・未確定の要件・追加検討が必要な点）

## 次のアクション
- （担当者・タスク内容・期限などを箇条書き）

---

以下が会議の文字起こしです：

{text}

以上のテンプレートに基づいて、Markdown形式の議事録を作成してください。

"""

def generate_maintenance_minutes_prompt(text: str) -> str:
    return f"""
以下は運用・保守フェーズの会議の不完全な文字起こしです。

あなたの仕事は、次のMarkdownテンプレートの形式に沿って、議事録を構成することです。
**テンプレートの構造を維持し、各セクションに該当する内容を記入してください。**

---

## 会議概要
- 会議の目的: システム運用・保守に関する状況確認
- 参加者: 不明

## 発生事象・問い合わせ内容
- （障害、問い合わせ、利用者からの報告内容などを記述）

## 対応状況と方針
- （現在の対応内容、方針、恒久対応の有無など）

## 次のアクション
- （対応者・タスク・期限を明確に）

---

以下が会議の文字起こしです：

{text}

以上のテンプレートを埋める形で、Markdown形式の議事録を作成してください。

"""

def generate_misc_minutes_prompt(text: str) -> str:
    return f"""
以下は業務に直接関係しない内容、またはその他分類の会議の不完全な文字起こしです。
あなたの仕事は、この会議の議事録を明確なMarkdown形式でまとめることです。

## 会議概要
- 会議の目的: 未分類 / 社内連絡 / 雑談 など
- 参加者: 不明の場合は「不明」と記載

## 話題の概要
- 話されたトピックを箇条書きで整理

## 特記事項
- 共有事項やちょっとしたメモがあれば記載

以下が会議の文字起こしです：
{text}
以上の形式で議事録を作成してください。
"""

def _get_gemini_response(prompt: str) -> str:
    """
    Gemini APIにプロンプトを送信し、応答を取得する内部ヘルパー関数。
    """
    if not _gemini_client:
        raise Exception("Gemini APIクライアントが初期化されていません。")

    try:
        # _gemini_client を通じて models コレクションにアクセスし、generate_content を呼び出す
        gemini_response = _gemini_client.models.generate_content(
            model=_gemini_model_name,
            contents=prompt
        )
        return gemini_response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
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
        print(f"分類結果のJSONパースに失敗しました: {e}. 元の応答: {json_str_response}")
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
    if not _gemini_client:
        return "Gemini APIキーが設定されていないか、クライアントの初期化に失敗したため、処理できませんでした。"

    try:
        # 1. 会議のカテゴリを分類
        category = classify_meeting_transcript(plain_text_transcript)
        print(f"会議のカテゴリ: {category}")

        # 2. 分類されたカテゴリに基づいて議事録を生成
        minutes_markdown = generate_meeting_minutes(plain_text_transcript, category)
        print("Markdown議事録の生成が完了しました。")
        return minutes_markdown

    except Exception as e:
        print(f"会議文字起こし処理全体でエラーが発生しました: {e}")
        return f"会議文字起こしの処理中にエラーが発生しました: {e}"