
FROM public.ecr.aws/lambda/python:3.9

# 作業ディレクトリを /var/task に設定（Lambda の標準）
WORKDIR /var/task

# requirements.txt をコンテナ内にコピー
COPY requirements.txt .

# requirements.txt に基づいて依存関係を /var/task ディレクトリにインストール
# -t . は、現在のディレクトリにインストールするという意味
# --no-cache-dir は、キャッシュを作成しないため、イメージサイズを小さく保つ
RUN pip install -r requirements.txt -t . --no-cache-dir

# Lambda 関数のコードをコンテナ内にコピー
COPY lambda_function.py .

# CMD は Lambda のハンドラを指定します。
# public.ecr.aws/lambda/python イメージはデフォルトでハンドラを読み込むため、
# 通常は不要ですが、明示的に追加することも可能です。
# CMD [ "lambda_function.lambda_handler" ]