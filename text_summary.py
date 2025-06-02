import re
from text_classify import classify_whole_transcript
import google.generativeai as genai
import json

# Gemini APIキーの設定
genai.configure(api_key="AIzaSyAw-h-4C0qxCuJyPnbBJOY_RgwUGXktBWQ")

# モデル選択（gemini-1.5-flash など）
model = genai.GenerativeModel("gemini-2.0-flash")

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

def output_meeting_minutes(text: str, category: str = None) -> str:
    if category == "プリセールス":
        prompt = generate_presales_minutes_prompt(text)
        response = model.generate_content(contents=prompt)
        return response.text
    elif category == "要件定義":
        prompt = generate_requirements_minutes_prompt(text)
        response = model.generate_content(contents=prompt)
        return response.text
    elif category == "運用保守":
        prompt = generate_maintenance_minutes_prompt(text)
        response = model.generate_content(contents=prompt)
        return response.text
    else:
        prompt = generate_misc_minutes_prompt(text)
        response = model.generate_content(contents=prompt)
        return response.text

if __name__ == "__main__":
    with open("texts/株式会社M&A承継機構様.txt", "r", encoding="utf-8") as f:
        full_text = f.read()

    json_str = classify_whole_transcript(full_text)

    print("=== 分類結果（元の出力） ===")
    print(json_str)

    # コードブロックの ```json と ``` を除去
    cleaned_str = re.sub(r"^```json|```$", "", json_str.strip(), flags=re.MULTILINE)

    try:
        json_classify = json.loads(cleaned_str)
        category = json_classify["category"]
    except json.JSONDecodeError as e:
        print("❌ JSON形式で読み込めませんでした。出力を確認してください。")
        raise e

    # 議事録生成
    md_output = output_meeting_minutes(full_text, category)

    # 表示
    print("=== Markdown議事録 ===")
    print(md_output)


