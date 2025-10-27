import io

def extract_text_from_vtt(vtt_content):
    """
    VTTコンテンツからプレーンテキストを抽出します。
    """
    lines = vtt_content.splitlines()
    extracted_text = []
    in_caption = False
    for line in lines:
        line = line.strip()
        if not line or line == "WEBVTT":
            in_caption = False # 空行やWEBVTTでリセット
            continue
        # タイムスタンプ行をスキップ
        if "-->" in line:
            in_caption = True # タイムスタンプの次の行からが本文
            continue
        # NOTEやSTYLEブロックをスキップ (より堅牢に)
        if line.startswith("NOTE") or line.startswith("STYLE"):
             in_caption = False
             continue
        # 本文行のみを抽出
        if in_caption:
             # HTMLタグのようなものがあれば除去 (簡易的)
             import re
             line = re.sub(r'<[^>]+>', '', line)
             # 発言者情報 (例: <v ->山田>) があれば除去
             line = re.sub(r'<v\s*[^>]*>.*?</v>', '', line)
             # 前後の空白を削除して追加
             cleaned_line = line.strip()
             if cleaned_line: # 空行でなければ追加
                extracted_text.append(cleaned_line)

    # 重複行を削除しつつ、順序を保持 (VTTによっては同じ内容が続くことがあるため)
    seen = set()
    unique_lines = []
    for line in extracted_text:
        if line not in seen:
            unique_lines.append(line)
            seen.add(line)

    return "\n".join(unique_lines)


def extract_text_from_txt(txt_content):
    """
    TXTコンテンツをそのまま返します。(前後の空白や空行は削除)
    """
    lines = [line.strip() for line in txt_content.splitlines()]
    # 完全な空行を除去
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)