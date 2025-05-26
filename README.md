# Discord Task Management Bot

サークル運営を支援するDiscord Botです。タスク管理とメール通知機能を提供します。

## 機能

- タスク管理
  - タスクの作成、編集、削除
  - 締切日管理
  - 自動リマインド
- Outlookメール連携
  - メール通知
  - OAuth2認証

## 技術スタック

- Python 3.11+
- Discord.py
- FastAPI
- SQLAlchemy
- PostgreSQL (Supabase)
- Poetry

## 開発環境のセットアップ

1. 必要なツールのインストール
```bash
# Poetryのインストール
brew install poetry

# 依存関係のインストール
poetry install
```

2. 環境変数の設定
```bash
# 環境変数テンプレートのコピー
cp config.example.env .env

# .envファイルを編集して必要な値を設定
```

3. データベースのセットアップ
```bash
# マイグレーションの実行
poetry run alembic upgrade head
```

4. 開発サーバーの起動
```bash
# Discord Botの起動
poetry run python src/discord_todo/bot/main.py

# FastAPI サーバーの起動（別ターミナルで）
poetry run uvicorn src.discord_todo.api.main:app --reload
```

## テスト

```bash
# テストの実行
poetry run pytest

# コードフォーマット
poetry run ruff format .

# リンター
poetry run ruff check .
```

## デプロイ

- Bot: Fly.io
- API: Vercel
- Database: Supabase

詳細なデプロイ手順は[デプロイガイド](docs/deployment.md)を参照してください。

## ライセンス

MIT License