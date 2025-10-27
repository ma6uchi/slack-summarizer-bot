import json
import os
import logging
import sys
from slack_sdk import WebClient

# インポートするモジュールを追加
import text_extractor
import ai_processor
import slack_utils

# --- ロガー設定 ---
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
# ---

# 環境変数からトークンとAPIキーを取得
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Slackクライアントの初期化
client = WebClient(token=SLACK_BOT_TOKEN)

# Gemini APIの設定 (古いSDK方式 ai_processor.py で初期化)
if GEMINI_API_KEY:
    ai_processor.set_gemini_client_and_model(GEMINI_API_KEY, model_name='gemini-2.0-flash')
else:
    logger.warning("GEMINI_API_KEYが設定されていません。Gemini APIは利用できません。")
    ai_processor.set_gemini_client_and_model(None)

def lambda_handler(event, context):
    body_content = {}
    if 'body' in event:
        try:
            body_content = json.loads(event['body'])
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse event body: {event.get('body')}")
            body_content = event # パース失敗時はそのまま使う (URL検証など)
    else:
        body_content = event

    # URL検証リクエストの処理
    if "challenge" in body_content:
        logger.info("Received URL verification request.")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'challenge': body_content['challenge']})
        }

    logger.info(f"Received event body: {json.dumps(body_content, indent=2)}")

    # Slackイベントヘッダーを取得
    headers = event.get('headers', {})
    logger.info(f"RECEIVED HEADERS: {json.dumps(headers, indent=2)}") # デバッグ用ログ

    # Slackリトライ検知 (修正版 slack_utils.py を使用)
    if slack_utils.is_slack_retry(headers):
        # リトライ理由もログに出力（デバッグ用）
        retry_reason = headers.get('X-Slack-Retry-Reason', 'Unknown')
        logger.warning(f"Detected Slack retry (Retry-Num: {headers.get('X-Slack-Retry-Num')}, Reason: {retry_reason}). Ignoring this event.")
        return {'statusCode': 200, 'body': json.dumps('OK (Retry Ignored)')}

    # --- メイン処理 ---
    event_data = body_content.get('event', {})
    event_type = event_data.get('type')
    channel_id = event_data.get('channel')
    user_id = event_data.get('user')
    ts = event_data.get('ts') # スレッド返信用のタイムスタンプ

    # アプリへのメンションイベントかチェック
    if event_type == 'app_mention':
        files = event_data.get('files')
        if files:
            logger.info("メンションとファイル添付を検知しました。")
            # 処理中のフィードバックメッセージを送信 (1回だけ送る)
            slack_utils.send_processing_message(client, channel_id, user_id, ts)

            for file_info in files:
                file_id = file_info.get('id')
                file_name = file_info.get('name')
                file_url_private = file_info.get('url_private')
                file_mimetype = file_info.get('mimetype')

                logger.info(f"File detected: ID={file_id}, Name={file_name}, MimeType={file_mimetype}")

                extracted_text = ""
                try:
                    # ファイルダウンロード
                    file_content_bytes = slack_utils.download_file(file_url_private, SLACK_BOT_TOKEN, binary_mode=True)
                    logger.info(f"File '{file_name}' のダウンロードが完了しました。")

                    # ファイルタイプに応じてテキスト抽出
                    if file_mimetype == 'text/vtt' or file_name.lower().endswith('.vtt'):
                        logger.info(f"VTTファイル '{file_name}' を処理します。")
                        vtt_content = file_content_bytes.decode('utf-8')
                        extracted_text = text_extractor.extract_text_from_vtt(vtt_content)
                    elif file_mimetype == 'text/plain' or file_name.lower().endswith('.txt'):
                        logger.info(f"TXTファイル '{file_name}' を処理します。")
                        txt_content = file_content_bytes.decode('utf-8')
                        extracted_text = text_extractor.extract_text_from_txt(txt_content)
                    else:
                        logger.warning(f"Unsupported file type: {file_name} ({file_mimetype})")
                        slack_utils.send_non_vtt_message(client, channel_id, user_id, file_name, file_mimetype, ts)
                        continue # 次のファイルへ

                    # Gemini APIで議事録生成
                    meeting_minutes_markdown = ai_processor.process_meeting_transcript(extracted_text)

                    # 結果をSlackに返信
                    slack_utils.send_summary_message(
                        client, channel_id, user_id, file_name, meeting_minutes_markdown, ts
                    )

                except Exception as e:
                    logger.error(f"File processing error for '{file_name}': {e}", exc_info=True)
                    slack_utils.send_error_message(client, channel_id, user_id, file_name, str(e), ts)
        else:
            # メンションのみの場合
            logger.info("メンションのみ（ファイル添付なし）を検知しました。")
            slack_utils.send_general_mention_message(client, channel_id, user_id, ts)

    # 正常終了応答
    return {
        'statusCode': 200,
        'body': json.dumps('OK')
    }

