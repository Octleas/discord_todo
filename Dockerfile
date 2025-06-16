FROM python:3.11-slim

WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetryのインストール
RUN pip install poetry

# Poetryの設定（仮想環境を作らない）
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# 依存関係のファイルをコピー
COPY pyproject.toml poetry.lock* ./

# 依存関係のインストール
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# アプリケーションのコードをコピー
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# 環境変数の設定
ENV PYTHONPATH=/app/src \
    ENVIRONMENT=production

# ポートの公開
EXPOSE 8000

# 起動スクリプトの作成
COPY start.sh ./
RUN chmod +x start.sh

# 起動スクリプトを実行
CMD ["./start.sh"] 