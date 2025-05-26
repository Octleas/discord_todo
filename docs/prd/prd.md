## プロダクト要件定義書（PRD）
# サークル運営支援Bot｜プロダクト要件ドキュメント（PRD）

---

## 1. 背景と目的

大学サークル運営では、メールの見逃しや業務のタスク漏れが発生しやすい。

すべての通知・管理をBotで完結できるようにすることで、運営業務の「見える化」と「共有化」を実現する。

---

## 2. 想定ユーザー

- サークル運営メンバー（会長・副会長・会計）
- Discordを日常的に使う小規模チーム
- Outlookメールを使って連絡を受け取っている

---

## 3. 機能構成

① タスク管理機能

- `/task add` コマンドでタスクを登録
- Supabase（PostgreSQL）に保存
- 締切・重要度に応じてFly.io上のBotがリマインド
- `/task done` または ✅リアクションで完了処理

② メール通知機能（Bot内蔵）

- `/mail connect` コマンドでOutlookアカウントをOAuth連携
- Vercel API経由でトークン取得・Supabaseに保存
- Fly.io上のBotがトークンを用いて定期メール取得（１日数回程度）
- 条件一致メールをDiscordにEmbed形式で通知

---

## 4. ユーザーフロー

＜タスク登録・進捗＞

ユーザーが `/task add` 実行

→ Vercel APIがSupabaseに保存

→ Fly.io Botがリマインド登録

→ Discord通知 → ✅または `/task done` で完了

＜メール通知＞

ユーザーが `/mail connect` 実行

→ Vercel APIでOAuth → トークンをSupabaseに保存

→ Fly.io Botが定期取得 → Discord通知

---

## 5. スラッシュコマンド一覧

- `/mail connect`：Outlook認証を開始し、メール連携を許可
- `/task add [タスク名] [@担当者] [締切日] [重要度] [要約]`：タスク登録
- `/task delete [id]`：タスク削除
- `/task edit [id]`：タスク編集
- `/task list`：未完了のタスク一覧表示
- `/task detail [id]`：指定タスクの詳細を表示
- `/task done [id]`：タスクを完了に設定

---

## 6. タスクデータ構造（Supabase PostgreSQL）

- task_id：自動付与されたタスク番号
- message_id：DiscordのメッセージID
- title：タスク名
- assigned_to：担当者（Discord ID）
- deadline：締切日
- importance：low / medium / high
- status：未完了 / 完了
- created_at：登録日時
- pdf_url：添付資料のURL（任意）
- summary：要約（手動入力）

---

## 7. 機能要件

- スラッシュコマンドでのタスク管理（Vercel）
- Supabase保存・読み出し・完了処理（Fly.io）
- APSchedulerによる自動リマインド（Fly.io）
- Outlook認証（OAuth2）とメール取得 → Discord通知（Vercel → Fly.io）

---

## 8. 技術構成

- Bot本体：Python（discord.py）@ Fly.io（常駐処理・リマインド）
- Web API：FastAPI @ Vercel（スラッシュコマンド処理／OAuth連携）
- データ保存：Supabase（PostgreSQL）
- メール連携：Microsoft Graph API（OAuth認証）

---

## 9. KPI（PoCで確認すべき指標）

- タスク登録数：週5件以上
- 完了率：80%以上
- メール通知成功数：週3件以上

---

## 10. PoC完了の定義

- OutlookメールがBot経由でDiscord通知される
- スラッシュコマンドでのタスク管理が動作（add→リマインド→done）
- Supabaseでタスク状態が保存・復元可能
- 実タスク3件以上での実運用とKPI記録あり

---

## 11. スケジュール（PoC開発：3週間）

第1週：Vercel API構築（/task add, /mail connect）＋Supabase接続

第2週：Fly.io Bot構築（discord.py）＋リマインド処理＋Supabase連携

第3週：Microsoft Graph APIでのメール取得・通知機能を追加