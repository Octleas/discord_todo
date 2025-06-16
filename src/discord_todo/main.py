from fastapi import FastAPI
from .api.mail_callback import router as mail_callback_router

app = FastAPI(
    title="Discord Todo Bot API",
    description="Discord Task Management Bot with Email Integration",
    version="1.0.0",
)

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """Fly.ioのヘルスチェック用エンドポイント"""
    return {
        "status": "healthy",
        "service": "discord-todo-bot",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Discord Todo Bot API",
        "status": "running",
        "docs": "/docs"
    }

# ルーターを組み込む
app.include_router(mail_callback_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("discord_todo.main:app", host="0.0.0.0", port=8000, reload=True) 