# API設計仕様書

## 1. 概要

このドキュメントでは、サークル運営支援Botのバックエンド（Vercel API）の設計仕様を定義します。

## 2. エンドポイント一覧

### タスク管理API

#### POST /api/tasks/add
タスクを新規作成します。

**リクエスト**
```json
{
  "guild_id": "string",
  "channel_id": "string",
  "title": "string",
  "assigned_to": "string",
  "deadline": "string",
  "importance": "low|medium|high",
  "summary": "string",
  "pdf_url": "string (optional)"
}
```

**レスポンス**
```json
{
  "task_id": "string",
  "message_id": "string",
  "status": "success|error",
  "message": "string"
}
```

#### DELETE /api/tasks/{task_id}
指定されたタスクを削除します。

**レスポンス**
```json
{
  "status": "success|error",
  "message": "string"
}
```

#### PUT /api/tasks/{task_id}
タスクを更新します。

**リクエスト**
```json
{
  "title": "string (optional)",
  "assigned_to": "string (optional)",
  "deadline": "string (optional)",
  "importance": "low|medium|high (optional)",
  "summary": "string (optional)",
  "pdf_url": "string (optional)"
}
```

**レスポンス**
```json
{
  "status": "success|error",
  "message": "string"
}
```

#### GET /api/tasks/list
未完了のタスク一覧を取得します。

**クエリパラメータ**
- guild_id: string
- channel_id: string (optional)

**レスポンス**
```json
{
  "tasks": [
    {
      "task_id": "string",
      "message_id": "string",
      "title": "string",
      "assigned_to": "string",
      "deadline": "string",
      "importance": "low|medium|high",
      "status": "pending|completed",
      "created_at": "string",
      "summary": "string",
      "pdf_url": "string"
    }
  ]
}
```

#### GET /api/tasks/{task_id}
指定されたタスクの詳細を取得します。

**レスポンス**
```json
{
  "task_id": "string",
  "message_id": "string",
  "title": "string",
  "assigned_to": "string",
  "deadline": "string",
  "importance": "low|medium|high",
  "status": "pending|completed",
  "created_at": "string",
  "summary": "string",
  "pdf_url": "string"
}
```

#### PUT /api/tasks/{task_id}/complete
タスクを完了状態に更新します。

**レスポンス**
```json
{
  "status": "success|error",
  "message": "string"
}
```

### メール連携API

#### GET /api/mail/auth
Outlookの認証URLを生成します。

**レスポンス**
```json
{
  "auth_url": "string"
}
```

#### POST /api/mail/callback
OAuth2コールバックを処理します。

**リクエスト**
```json
{
  "code": "string",
  "guild_id": "string",
  "user_id": "string"
}
```

**レスポンス**
```json
{
  "status": "success|error",
  "message": "string"
}
```

## 3. エラーレスポンス

すべてのAPIエンドポイントは、エラー時に以下の形式でレスポンスを返します：

```json
{
  "status": "error",
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

## 4. 認証

- すべてのAPIリクエストには`Authorization`ヘッダーにDiscordのBotトークンが必要です
- メール連携APIは、Microsoft Graph APIのOAuth2認証フローを使用します

## 5. レート制限

- 1分あたり60リクエストまで
- 超過した場合は429 Too Many Requestsを返します 