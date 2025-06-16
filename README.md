# サークル運営支援Bot

> **Discord上でタスク管理とメール通知を統合し、サークル運営を効率化するボットアプリケーション**

---

## 📋 概要

大学サークル運営では、メールの見逃しやタスクの漏れが頻繁に発生します。このBotは、Discord上ですべての運営業務を一元管理し、「見える化」と「共有化」を実現することで、効率的なサークル運営を支援します。

## 🎯 対象ユーザー

- **サークル運営メンバー**（会長・副会長・会計など）
- **Discordを日常的に使用する小規模チーム**
- **Outlookメールでの連絡を受け取っている組織**

---

## ✨ 主要機能

### 🔔 メール通知機能
- Microsoft Outlook/Office365メールの自動取得・通知
- OAuth2.0による安全な認証
- 定期的なメールチェック（30分間隔）
- Discord Embedでの美しい通知表示

### 📝 タスク管理機能
- スラッシュコマンドによる直感的なタスク操作
- 担当者・締切・重要度の設定
- 自動リマインド機能
- リアクションまたはコマンドでの完了処理

---

## 🛠️ 技術構成

- **Bot本体**: Python 3.11+ (discord.py)
- **Web API**: FastAPI
- **データベース**: Supabase (PostgreSQL)
- **認証**: Microsoft Graph API (OAuth2.0)
- **スケジューラー**: APScheduler
- **デプロイ**: Fly.io対応

---

## 🚀 使い方

### 初期設定

1. **環境変数の設定**
   ```bash
   cp env.example .env
   # .envファイルを編集して必要な環境変数を設定
   ```

2. **依存関係のインストール**
   ```bash
   poetry install
   ```

3. **データベースのセットアップ**
   ```bash
   poetry run alembic upgrade head
   ```

4. **ボットの起動**
   ```bash
   poetry run python -m discord_todo
   ```

### Docker Composeでの起動（推奨）

```bash
# 環境変数ファイルを準備
cp env.example .env
# .envファイルを編集

# Docker Composeで起動
docker-compose up -d

# ログの確認
docker-compose logs -f
```

### Fly.ioへのデプロイ

本番環境でのデプロイ手順は[deploy.md](deploy.md)を参照してください。

#### クイックデプロイ

```bash
# Fly.io CLIのインストール
brew install flyctl  # macOS
# または
curl -L https://fly.io/install.sh | sh  # Linux

# ログイン
flyctl auth login

# 環境変数の設定
flyctl secrets set DISCORD_TOKEN="your_token"
flyctl secrets set DATABASE_URL="your_supabase_url"
# その他の環境変数...

# デプロイ
flyctl deploy

# 状況確認
flyctl status
flyctl logs
```

### スラッシュコマンド一覧

#### 📧 メール連携コマンド

| コマンド | 説明 | 使用例 |
|---------|-----|--------|
| `/mail-connect` | Outlookアカウントとの連携を開始 | `/mail-connect` |
| `/mail-status` | 連携状態とトークン有効期限を確認 | `/mail-status` |
| `/mail-test` | メール取得テスト（1-10件） | `/mail-test limit:5 show_content:true` |
| `/mail-notify` | 通知機能のテスト実行 | `/mail-notify limit:3 skip_notification:false` |
| `/mail-disconnect` | メール連携を解除 | `/mail-disconnect` |

#### 📋 タスク管理コマンド

| コマンド | 説明 | 使用例 |
|---------|-----|--------|
| `/task-add` | 新しいタスクを追加 | `/task-add title:"会議準備" assignee:@user deadline:"2024-12-31" importance:high` |
| `/task-list` | 未完了タスクの一覧表示 | `/task-list` |
| `/task-complete` | タスクを完了状態に変更 | `/task-complete task_id:1` |
| `/task-delete` | タスクを削除 | `/task-delete task_id:1` |

---

## 📊 データ構造

### タスクテーブル（tasks）
```sql
- id: タスクID（自動生成）
- guild_id: DiscordサーバーID
- title: タスク名
- assignee_id: 担当者のDiscordユーザーID
- deadline: 締切日時
- importance: 重要度（low/medium/high）
- completed: 完了フラグ
- created_at: 作成日時
- updated_at: 更新日時
```

### メール連携テーブル（mail_connections）
```sql
- id: 連携ID（自動生成）
- guild_id: DiscordサーバーID
- user_id: ユーザーのDiscordID
- email: 連携したメールアドレス
- access_token: アクセストークン（暗号化）
- refresh_token: リフレッシュトークン（暗号化）
- token_expires_at: トークン有効期限
- last_checked_at: 最終チェック日時
```

---

## 🔧 設定方法

### 環境変数

```bash
# Discord Bot
DISCORD_TOKEN=your_discord_bot_token
DISCORD_APPLICATION_ID=your_application_id

# Microsoft Graph API
MICROSOFT_CLIENT_ID=your_azure_app_client_id
MICROSOFT_CLIENT_SECRET=your_azure_app_client_secret
MICROSOFT_TENANT_ID=common

# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Azure App Registration設定

1. Azure Portalで新しいアプリケーションを登録
2. 以下のAPIアクセス許可を追加：
   - `Mail.Read`
   - `User.Read`
   - `offline_access`
3. リダイレクトURIを設定：`http://localhost:8000/api/mail/callback`
4. 「個人用Microsoftアカウント」を有効化

---

## 🏃‍♂️ 実行例

### メール連携の設定
```
1. /mail-connect を実行
2. 表示されたURLでMicrosoftアカウントにログイン
3. アクセス許可を承認
4. /mail-status で連携状態を確認
```

### タスクの管理
```
1. /task-add title:"予算申請書作成" assignee:@田中 deadline:"2024-12-25 17:00" importance:high
2. /task-list で進捗確認
3. /task-complete task_id:1 で完了処理
```
---

## 🛡️ セキュリティ

### データ保護
- OAuth2.0による安全な認証
- トークンの暗号化保存
- 最小権限の原則に基づくAPI権限
- 定期的なトークン更新

### プライバシー
- メール内容は一時的な表示のみ
- 個人情報の永続的な保存なし
- ユーザーによるデータ削除権の保証


### ログの確認
```bash
# ボット実行時のデバッグログ
poetry run python -m discord_todo
```

このプロジェクトの開発にあたり、以下のオープンソースプロジェクトを使用させていただいています：

- [discord.py](https://github.com/Rapptz/discord.py)
- [FastAPI](https://github.com/tiangolo/fastapi)
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy)
- [APScheduler](https://github.com/agronholm/apscheduler)

---