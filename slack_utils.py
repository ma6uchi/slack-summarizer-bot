import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def is_slack_retry(headers):
    """
    Slackイベントのリトライかどうかを判定します。
    """
    return 'X-Slack-Retry-Num' in headers and headers['X-Slack-Retry-Num'] != '0'

def send_message(client, channel, text, thread_ts=None, file_upload=False, title=None, content=None, filetype=None, initial_comment=None):
    """
    Slackにメッセージを送信する汎用関数。
    必要に応じてファイルアップロードも対応。
    """
    try:
        if file_upload:
            client.files_upload_v2(
                channel=channel,
                content=content,
                title=title,
                filetype=filetype,
                initial_comment=initial_comment,
                thread_ts=thread_ts # スレッドに投稿するための引数を追加
            )
        else:
            client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
    except SlackApiError as e:
        print(f"Error sending Slack message: {e.response['error']}")
        raise # エラーを上位に伝える

def send_processing_message(client, channel_id, user_id, ts):
    """
    処理開始のフィードバックメッセージを送信します。
    """
    send_message(
        client,
        channel=channel_id,
        text=f"<@{user_id}>さん、VTTファイルを検知しました。要約処理を開始しますね！少し時間がかかります。",
        thread_ts=ts
    )

def download_file(file_url_private, slack_bot_token):
    """
    Slackからファイルをダウンロードします。
    """
    headers = {"Authorization": f"Bearer {slack_bot_token}"}
    try:
        response = requests.get(file_url_private, headers=headers, stream=True)
        response.raise_for_status()

        vtt_content = ""
        for chunk in response.iter_content(chunk_size=8192):
            try:
                vtt_content += chunk.decode('utf-8')
            except UnicodeDecodeError:
                print("Warning: UnicodeDecodeError encountered, trying latin-1.")
                vtt_content += chunk.decode('latin-1', errors='ignore')
        return vtt_content
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error downloading file: {e}") # 例外を再スロー

def send_summary_message(client, channel_id, user_id, file_name, summarized_text, ts):
    """
    要約結果をSlackに返信します。
    """
    if len(summarized_text) > 3000:
        send_message(
            client,
            channel=channel_id,
            file_upload=True,
            content=summarized_text,
            title=f"{file_name} の要約",
            filetype="text",
            initial_comment=f"<@{user_id}>さん、ファイル `{file_name}` の要約です。長いためファイルとして添付しました。",
            thread_ts=ts # ファイルアップロード時もスレッドに投稿
        )
    else:
        send_message(
            client,
            channel=channel_id,
            text=f"<@{user_id}>さん、ファイル `{file_name}` の要約です:\n```{summarized_text}```",
            thread_ts=ts
        )

def send_error_message(client, channel_id, user_id, file_name, error_message, ts):
    """
    エラーメッセージをSlackに送信します。
    """
    send_message(
        client,
        channel=channel_id,
        text=f"<@{user_id}>さん、ファイル `{file_name}` の処理中にエラーが発生しました: {error_message}",
        thread_ts=ts
    )

def send_non_vtt_message(client, channel_id, user_id, file_name, file_mimetype, ts):
    """
    VTTファイル以外が添付された場合のメッセージを送信します。
    """
    send_message(
        client,
        channel=channel_id,
        text=f"<@{user_id}>さん、添付されたファイル `{file_name}` はVTTファイルではないようです。\n(MIME Type: `{file_mimetype}`)\nVTTファイルを添付してください。",
        thread_ts=ts
    )

def send_general_mention_message(client, channel_id, user_id, ts):
    """
    メンションされたがファイル添付がない場合のメッセージを送信します。
    """
    send_message(
        client,
        channel=channel_id,
        text=f"<@{user_id}>さん、メンションありがとう！VTTファイルを添付してくれれば要約するよ！",
        thread_ts=ts
    )