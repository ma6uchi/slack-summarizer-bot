import google.generativeai as genai

# Gemini APIキーの設定
genai.configure(api_key="AIzaSyAw-h-4C0qxCuJyPnbBJOY_RgwUGXktBWQ")

# モデル選択（gemini-1.5-flash など）
model = genai.GenerativeModel("gemini-1.5-flash")

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


def classify_whole_transcript(plain_text: str) -> str:
    prompt = generate_classify_meeting_prompt(plain_text)
    response = model.generate_content(contents=prompt)
    return response.text

if __name__ == "__main__":
    with open("texts/株式会社M&A承継機構様.txt", "r", encoding="utf-8") as f:
        full_text = f.read()

    json_classify = classify_whole_transcript(full_text)

    print("=== 分類 ===")
    print(json_classify)

