import json
import os
from slack_sdk import WebClient
import google.generativeai as genai

# インポートするモジュールを追加
from . import slack_utils
from . import vtt_parser
from . import ai_processor

# 環境変数からトークンとAPIキーを取得
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = WebClient(token=SLACK_BOT_TOKEN)

# Gemini APIの設定
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_processor.set_gemini_model('gemini-pro') # Geminiモデルの設定を別ファイルに委譲
else:
    print("GEMINI_API_KEYが設定されていません。Gemini APIは利用できません。")
    ai_processor.set_gemini_model(None) # Noneを設定してGeminiが利用不可であることを伝える

def lambda_handler(event, context):
    body_content = {}
    if 'body' in event:
        try:
            body_content = json.loads(event['body'])
        except json.JSONDecodeError:
            body_content = event
    else:
        body_content = event

    if "challenge" in body_content:
        print("Received URL verification request.")
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'challenge': body_content['challenge']})
        }

    print(f"Received event body: {json.dumps(body_content, indent=2)}")

    # Slackイベントのリトライを検知
    headers = event.get('headers', {})
    if slack_utils.is_slack_retry(headers): # ヘルパー関数を呼び出す
        print(f"Detected Slack retry (Retry-Num: {headers['X-Slack-Retry-Num']}). Ignoring this event.")
        return {'statusCode': 200, 'body': json.dumps('OK')}

    event_data = body_content.get('event', {})
    event_type = event_data.get('type')
    channel_id = event_data.get('channel')
    user_id = event_data.get('user')
    ts = event_data.get('ts')

    if event_type == 'app_mention':
        files = event_data.get('files')
        if files:
            print("メンションとファイル添付を検知しました。")
            slack_utils.send_processing_message(client, channel_id, user_id, ts)

            for file_info in files:
                file_id = file_info.get('id')
                file_name = file_info.get('name')
                file_url_private = file_info.get('url_private')
                file_mimetype = file_info.get('mimetype')

                print(f"File detected: ID={file_id}, Name={file_name}, MimeType={file_mimetype}")

                if file_mimetype == 'text/vtt' or file_name.lower().endswith('.vtt'):
                    print(f"VTTファイル '{file_name}' をダウンロードします。")
                    try:
                        vtt_content = slack_utils.download_file(file_url_private, SLACK_BOT_TOKEN)
                        print(f"VTTファイル '{file_name}' のダウンロードが完了しました。")
                        
                        extracted_text = vtt_parser.extract_text_from_vtt(vtt_content) # VTTパーサーを呼び出す
                        summarized_text = ai_processor.get_summary_from_gemini(extracted_text) # Geminiプロセッサーを呼び出す

                        slack_utils.send_summary_message(
                            client, channel_id, user_id, file_name, summarized_text, ts
                        )

                    except Exception as e: # より広範なエラーをキャッチ
                        print(f"File processing error: {e}")
                        slack_utils.send_error_message(client, channel_id, user_id, file_name, str(e), ts)
                else:
                    slack_utils.send_non_vtt_message(client, channel_id, user_id, file_name, file_mimetype, ts)
        else:
            slack_utils.send_general_mention_message(client, channel_id, user_id, ts)

    return {
        'statusCode': 200,
        'body': json.dumps('OK')
    }