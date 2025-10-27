# AWSが提供する公式のPython 3.11 Lambdaベースイメージを使用
FROM public.ecr.aws/lambda/python:3.11

# 作業ディレクトリを/var/taskに設定 (Lambdaの標準)
WORKDIR /var/task

# 依存ライブラリの定義ファイルをコンテナにコピー
COPY requirements.txt .

# pipを使って依存ライブラリをインストール
# --upgrade は不要 (古いSDK 0.8.5 で動作させるため)
RUN pip install -r requirements.txt --no-cache-dir

# ソースコード (.pyファイル) をコンテナにコピー
COPY lambda_function.py .
COPY ai_processor.py .
COPY slack_utils.py .
COPY text_extractor.py .

# プロンプトファイルが格納されたディレクトリをコピー
COPY prompts/ ./prompts/

# Lambdaが呼び出すハンドラを指定
# 書式: <ファイル名>.<関数名>
CMD [ "lambda_function.lambda_handler" ]
