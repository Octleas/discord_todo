# Fly.ioデプロイメントガイド

このガイドでは、Discord Todo BotをFly.ioにデプロイする手順を説明します。

## 前提条件

1. **Fly.ioアカウント**の作成
2. **flyctl CLI**のインストール
3. **Azure App Registration**の設定完了
4. **Supabaseプロジェクト**の準備

## 1. Fly.io CLIのインストール

### macOS
```bash
brew install flyctl
```

### Linux/WSL
```bash
curl -L https://fly.io/install.sh | sh
```

### Windows
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

## 2. Fly.ioにログイン

```bash
flyctl auth login
```

## 3. アプリケーションの初期化

```bash
# プロジェクトディレクトリに移動
cd discord_todo

# Fly.ioアプリを初期化（既存のfly.tomlがある場合はスキップ）
flyctl apps create discord-todo-bot
```

## 4. 環境変数の設定

### 必須の環境変数を設定

```bash
# Discord Bot設定
flyctl secrets set DISCORD_TOKEN="your_discord_bot_token"
flyctl secrets set DISCORD_APPLICATION_ID="your_application_id"

# Microsoft Graph API設定
flyctl secrets set MICROSOFT_CLIENT_ID="your_azure_app_client_id"
flyctl secrets set MICROSOFT_CLIENT_SECRET="your_azure_app_client_secret"
flyctl secrets set MICROSOFT_TENANT_ID="common"

# データベース設定（Supabase）
flyctl secrets set DATABASE_URL="postgresql://user:password@host:port/database"

# API設定
flyctl secrets set API_HOST="0.0.0.0"
flyctl secrets set API_PORT="8000"
```

### 環境変数の確認
```bash
flyctl secrets list
```

## 5. Azure App Registrationの更新

デプロイ後のURLに合わせてリダイレクトURIを更新：

1. Azure Portalにアクセス
2. App Registrationを選択
3. 「認証」セクションで以下を追加：
   ```
   https://your-app-name.fly.dev/api/mail/callback
   ```

## 6. デプロイの実行

### 初回デプロイ
```bash
flyctl deploy
```

### デプロイ状況の確認
```bash
# デプロイ状況を確認
flyctl status

# ログを確認
flyctl logs

# アプリケーションを開く
flyctl open
```

## 7. データベースマイグレーション

デプロイ後、データベースマイグレーションが自動実行されます。
手動で実行する場合：

```bash
flyctl ssh console
poetry run alembic upgrade head
exit
```

## 8. 動作確認

### ヘルスチェック
```bash
curl https://your-app-name.fly.dev/health
```

### API確認
```bash
curl https://your-app-name.fly.dev/
```

### Discord Botの確認
Discordサーバーでスラッシュコマンドが利用可能か確認

## 9. 監視とメンテナンス

### ログの監視
```bash
# リアルタイムログ
flyctl logs -f

# 特定の時間範囲のログ
flyctl logs --since="1h"
```

### アプリケーションの再起動
```bash
flyctl apps restart discord-todo-bot
```

### スケーリング
```bash
# インスタンス数を変更
flyctl scale count 2

# メモリを変更
flyctl scale memory 2048
```

## 10. 更新とデプロイ

### コードの更新後
```bash
# 変更をコミット
git add .
git commit -m "Update: 機能追加"

# 再デプロイ
flyctl deploy
```

### 環境変数の更新
```bash
flyctl secrets set VARIABLE_NAME="new_value"
flyctl apps restart discord-todo-bot
```

## 11. トラブルシューティング

### よくある問題

#### 1. デプロイが失敗する
```bash
# ビルドログを確認
flyctl logs --app discord-todo-bot

# Dockerfileの構文確認
docker build -t test .
```

#### 2. Botが起動しない
```bash
# 環境変数を確認
flyctl secrets list

# SSH接続してデバッグ
flyctl ssh console
```

#### 3. データベース接続エラー
```bash
# DATABASE_URLの確認
flyctl secrets list | grep DATABASE

# 接続テスト
flyctl ssh console
poetry run python -c "from discord_todo.db.session import engine; print('DB OK')"
```

#### 4. メール認証が失敗する
- Azure App RegistrationのリダイレクトURIを確認
- HTTPS URLが正しく設定されているか確認

### ログレベルの変更
```bash
flyctl secrets set LOG_LEVEL="DEBUG"
flyctl apps restart discord-todo-bot
```

## 12. セキュリティ設定

### IPアクセス制限（オプション）
```bash
# 特定のIPからのみアクセス許可
flyctl ips allocate-v4 --region nrt
```

### SSL証明書の確認
```bash
flyctl certs list
flyctl certs show your-app-name.fly.dev
```

## 13. バックアップとリストア

### 設定のバックアップ
```bash
# fly.tomlをバックアップ
cp fly.toml fly.toml.backup

# 環境変数をエクスポート
flyctl secrets list > secrets.backup
```

### アプリケーションの削除
```bash
flyctl apps destroy discord-todo-bot
```

## 14. 費用の監視

### 使用量の確認
```bash
flyctl dashboard billing
```

### 自動停止の設定
fly.tomlで以下を設定済み：
```toml
[http_service]
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1
```

---

## サポート

問題が発生した場合：

1. **ログの確認**: `flyctl logs`
2. **GitHub Issues**: バグ報告
3. **Fly.io Community**: https://community.fly.io/
4. **Discord**: プロジェクトのDiscordサーバー

---

**最終更新**: 2024年12月16日 