import re

def extract_text_from_vtt(vtt_content):
    """
    VTTファイルの内容から純粋なテキストを抽出します。
    """
    lines = vtt_content.split('\n')
    extracted_lines = []
    for line in lines:
        # タイムスタンプ行をスキップ
        if re.match(r'^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', line):
            continue
        # WEBVTTヘッダーや空行、NOTE行をスキップ
        if line.strip() in ["WEBVTT", ""] or line.startswith("NOTE"):
            continue
        extracted_lines.append(line.strip())
    return " ".join(extracted_lines)