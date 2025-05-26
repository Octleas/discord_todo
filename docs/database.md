# データベース設計仕様書

## 1. 概要

このドキュメントでは、サークル運営支援Botで使用するSupabase（PostgreSQL）のデータベース設計仕様を定義します。

## 2. テーブル一覧

### tasks（タスク管理テーブル）

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|----------|------|------------|------|
| task_id | uuid | NO | uuid_generate_v4() | タスクの一意識別子 |
| guild_id | varchar(255) | NO | - | DiscordサーバーID |
| channel_id | varchar(255) | NO | - | DiscordチャンネルID |
| message_id | varchar(255) | NO | - | DiscordメッセージID |
| title | varchar(255) | NO | - | タスクのタイトル |
| assigned_to | varchar(255) | NO | - | 担当者のDiscord ID |
| deadline | timestamp with time zone | NO | - | 締切日時 |
| importance | enum('low', 'medium', 'high') | NO | 'medium' | 重要度 |
| status | enum('pending', 'completed') | NO | 'pending' | タスクの状態 |
| created_at | timestamp with time zone | NO | now() | 作成日時 |
| updated_at | timestamp with time zone | NO | now() | 更新日時 |
| summary | text | YES | NULL | タスクの要約 |
| pdf_url | varchar(1024) | YES | NULL | 添付資料のURL |

**インデックス**
- PRIMARY KEY (task_id)
- INDEX idx_guild_channel (guild_id, channel_id)
- INDEX idx_assigned_to (assigned_to)
- INDEX idx_status_deadline (status, deadline)

### mail_connections（メール連携テーブル）

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|----------|------|------------|------|
| connection_id | uuid | NO | uuid_generate_v4() | 連携の一意識別子 |
| guild_id | varchar(255) | NO | - | DiscordサーバーID |
| user_id | varchar(255) | NO | - | DiscordユーザーID |
| email | varchar(255) | NO | - | 連携したOutlookメールアドレス |
| access_token | text | NO | - | Outlookアクセストークン（暗号化） |
| refresh_token | text | NO | - | Outlookリフレッシュトークン（暗号化） |
| token_expires_at | timestamp with time zone | NO | - | トークン有効期限 |
| created_at | timestamp with time zone | NO | now() | 作成日時 |
| updated_at | timestamp with time zone | NO | now() | 更新日時 |
| last_checked_at | timestamp with time zone | YES | NULL | 最後のメール確認日時 |

**インデックス**
- PRIMARY KEY (connection_id)
- UNIQUE INDEX idx_guild_user (guild_id, user_id)
- INDEX idx_token_expires (token_expires_at)

### mail_notifications（メール通知履歴テーブル）

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|----------|------|------------|------|
| notification_id | uuid | NO | uuid_generate_v4() | 通知の一意識別子 |
| connection_id | uuid | NO | - | mail_connectionsテーブルの外部キー |
| message_id | varchar(255) | NO | - | メールのMessage-ID |
| subject | varchar(255) | NO | - | メールの件名 |
| sender | varchar(255) | NO | - | 送信者のメールアドレス |
| received_at | timestamp with time zone | NO | - | メール受信日時 |
| notified_at | timestamp with time zone | NO | now() | Discord通知日時 |
| discord_message_id | varchar(255) | NO | - | 通知したDiscordメッセージID |

**インデックス**
- PRIMARY KEY (notification_id)
- FOREIGN KEY (connection_id) REFERENCES mail_connections(connection_id)
- UNIQUE INDEX idx_message_id (message_id)
- INDEX idx_received_at (received_at)

## 3. セキュリティ要件

### データ暗号化
- アクセストークンとリフレッシュトークンは、保存前に暗号化する必要があります
- 暗号化にはAES-256-GCMを使用し、キーはSupabaseのVault機能で管理します

### アクセス制御
- Row Level Security (RLS)を使用して、以下のポリシーを実装：
  - タスクは同じguild_idに属するユーザーのみが参照可能
  - メール連携情報は作成したユーザーのみが参照可能
  - 通知履歴は関連するメール連携のユーザーのみが参照可能

### バックアップ
- Supabaseの自動バックアップを有効化（日次）
- バックアップ保持期間：30日

## 4. パフォーマンス要件

### インデックス最適化
- 頻繁に使用されるクエリに対して適切なインデックスを作成
- 特に以下のクエリのパフォーマンスを重視：
  - 未完了タスクの一覧取得
  - 期限切れタスクの検索
  - トークン有効期限切れの検索

### キャッシュ戦略
- 読み取り頻度の高いデータに対してSupabaseのキャッシュを活用
- キャッシュ有効期間：
  - タスク一覧：60秒
  - タスク詳細：300秒

## 5. マイグレーション管理

- マイグレーションはSupabase CLIを使用して管理
- マイグレーションファイルは`supabase/migrations`ディレクトリに配置
- 本番環境へのマイグレーションは必ずステージング環境でテスト後に実行

## 6. 監視とメンテナンス

### 監視項目
- データベースサイズ
- クエリパフォーマンス
- 接続数
- エラーレート

### メンテナンス
- 定期的なVACUUM実行（週次）
- 不要なデータの定期的なクリーンアップ（月次）
  - 完了後30日以上経過したタスク
  - 90日以上更新のないメール連携 