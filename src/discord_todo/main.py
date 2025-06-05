from fastapi import FastAPI
from .api.mail_callback import router as mail_callback_router

app = FastAPI()

# ルーターを組み込む
app.include_router(mail_callback_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("discord_todo.main:app", host="0.0.0.0", port=8000, reload=True) 