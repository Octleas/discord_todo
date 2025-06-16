#!/bin/bash

# エラー時は即座に終了
set -e

echo "🚀 Discord Todo Botを起動中..."

# データベースマイグレーションを実行
echo "📊 データベースマイグレーションを実行..."
poetry run alembic upgrade head

# FastAPIサーバーをバックグラウンドで起動
echo "🌐 FastAPIサーバーを起動..."
poetry run uvicorn discord_todo.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# 少し待ってからDiscordボットを起動
echo "⏳ FastAPIサーバーの起動を待機中..."
sleep 5

# Discordボットを起動
echo "🤖 Discordボットを起動..."
poetry run python -m discord_todo &
BOT_PID=$!

# プロセスの終了を待機
wait_for_process() {
    local pid=$1
    local name=$2
    while kill -0 $pid 2>/dev/null; do
        sleep 1
    done
    echo "❌ $name が終了しました"
}

# 終了処理の設定
cleanup() {
    echo "🛑 シャットダウン処理を開始..."
    kill $FASTAPI_PID 2>/dev/null || true
    kill $BOT_PID 2>/dev/null || true
    wait $FASTAPI_PID 2>/dev/null || true
    wait $BOT_PID 2>/dev/null || true
    echo "✅ シャットダウン完了"
    exit 0
}

trap cleanup SIGTERM SIGINT

echo "✅ すべてのサービスが起動しました"
echo "   - FastAPI: http://0.0.0.0:8000"
echo "   - Discord Bot: アクティブ"

# どちらかのプロセスが終了するまで待機
while kill -0 $FASTAPI_PID 2>/dev/null && kill -0 $BOT_PID 2>/dev/null; do
    sleep 5
done

# どちらかのプロセスが終了した場合
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "❌ FastAPIサーバーが予期せず終了しました"
elif ! kill -0 $BOT_PID 2>/dev/null; then
    echo "❌ Discordボットが予期せず終了しました"
fi

cleanup 