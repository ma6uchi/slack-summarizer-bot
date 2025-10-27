import requests
import json
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# Slackメッセージの最大文字長 (これを超えるとファイルとしてアップロード)
MAX_MESSAGE_LENGTH = 3000

# def is_slack_retry(headers):
#     """
#     Slackイベントのリトライを検知します。
#     """
#     return 'x-slack-retry-num' in headers and headers['x-slack-retry-num'] != '0'

def is_slack_retry(headers):
    """
    Slackイベントのリトライを検知します。
    """
    logger.info("--- slack_utils.py: is_slack_retry CALLED ---")
    
    # ★★★ ヘッダー名を小文字 'x-slack-retry-num' に修正 ★★★
    header_key = 'x-slack-retry-num' 
    
    is_retry = header_key in headers
    logger.info(f"Checking for header '{header_key}'. Found: {is_retry}") # 検知結果をログに出力
    return is_retry

def send_message(client, channel, text, thread_ts=None, file_upload=False, title=None, content=None, filetype=None, initial_comment=None):
    """
    Slackにメッセージを送信する汎用関数。(現在は直接未使用)
    """
    try:
        if file_upload:
            # files_upload_v2 は filetype 引数をサポートしないので削除
            client.files_upload_v2(
                channel=channel,
                content=content,
                title=title,
                initial_comment=initial_comment,
                thread_ts=thread_ts
            )
        else:
            client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
    except SlackApiError as e:
        logger.error(f"Error sending Slack message: {e.response['error']}")
        # エラーの詳細（needed scopeなど）もログに出力
        logger.error(f"Slack API Response: {e.response}")
        raise

def send_processing_message(client, channel_id, user_id, ts):
    """
    ファイル処理中であることをユーザーに通知するメッセージを送信します。
    """
    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=ts,
            text=f"<@{user_id}> ファイルを受信しました。内容を処理中です... ⏳" # ユーザーメンションを追加
        )
    except Exception as e:
        logger.error(f"Error sending processing message: {e}")

def download_file(file_url, slack_bot_token, binary_mode=False):
    """
    指定されたURLからファイルをダウンロードします。
    """
    headers = {"Authorization": f"Bearer {slack_bot_token}"}
    try:
        response = requests.get(file_url, headers=headers)
        response.raise_for_status() # HTTPエラーがあれば例外を発生
        if binary_mode:
            return response.content
        else:
            # Content-Typeを見てエンコーディングを推測 (より堅牢に)
            response.encoding = response.apparent_encoding
            return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"ファイルのダウンロードに失敗しました: {file_url}, Error: {e}")
        raise # エラーを上位に伝播

def send_summary_message(client, channel_id, user_id, file_name, summarized_text, ts):
    """
    議事録の要約結果をSlackに送信します。
    """
    initial_comment = f"<@{user_id}> '{file_name}' の議事録ができました！ ✨"
    try:
        if len(summarized_text) > MAX_MESSAGE_LENGTH:
            logger.info(f"要約テキストが{MAX_MESSAGE_LENGTH}文字を超えているためファイルとしてアップロード: {len(summarized_text)}文字")
            # files_upload_v2 に合わせて filetype を削除
            client.files_upload_v2(
                channel=channel_id,
                content=summarized_text,
                title=f"{file_name}_summary.md", # 拡張子を .md に
                initial_comment=initial_comment + f"\n\n文字数が多いためファイルで送信します。\n```{summarized_text[:200]}...```", # プレビュー少し長く
                thread_ts=ts
            )
        else:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=ts,
                text=initial_comment + f"\n\n```{summarized_text}```",
                mrkdwn=True
            )
    except SlackApiError as e:
        # missing_scope エラーなどを捕捉
        logger.error(f"Error sending summary message: {e.response['error']}")
        logger.error(f"Slack API Response: {e.response}")
        error_details = f"議事録の送信に失敗しました ({e.response.get('error', 'unknown error')})。"
        # files:write権限がない場合のエラーメッセージを追加
        if e.response.get('error') == 'missing_scope' and 'files:write' in e.response.get('needed',''):
             error_details += "\nSlackアプリに `files:write` スコープが不足している可能性があります。"
        send_error_message(client, channel_id, user_id, file_name, error_details, ts)
    except Exception as e:
        logger.error(f"Unexpected error sending summary message: {e}", exc_info=True)
        send_error_message(client, channel_id, user_id, file_name, "予期せぬエラーで議事録の送信に失敗しました。", ts)


def send_error_message(client, channel_id, user_id, file_name, error_details, ts):
    """
    エラーメッセージをSlackに送信します。
    """
    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=ts,
            text=f"<@{user_id}> 😥 '{file_name}' の処理中にエラーが発生しました。\n> {error_details}"
        )
    except Exception as e:
        logger.error(f"Error sending error message itself: {e}")

def send_non_vtt_message(client, channel_id, user_id, file_name, file_mimetype, ts):
    """
    VTT、TXTファイル以外が添付された場合のメッセージを送信します。
    """
    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=ts,
            text=f"<@{user_id}> '{file_name}' (`{file_mimetype}`) は未対応の形式です。\n`.vtt` または `.txt` ファイルを添付してください。"
        )
    except Exception as e:
        logger.error(f"Error sending non-VTT/TXT message: {e}")

def send_general_mention_message(client, channel_id, user_id, ts):
    """
    ファイルが添付されていないメンションの場合のメッセージを送信します。
    """
    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=ts,
            text=f"<@{user_id}> `.vtt` または `.txt` ファイルを添付してメンションすると、議事録を作成します。"
        )
    except Exception as e:
        logger.error(f"Error sending general mention message: {e}")