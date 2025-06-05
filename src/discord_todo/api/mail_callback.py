from fastapi import APIRouter, Request, HTTPException, Depends, Query
import httpx
import os
from src.discord_todo.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.discord_todo.db.session import get_db
from src.discord_todo.models.mail import MailConnection

router = APIRouter()

@router.get("/api/mail/callback")
async def mail_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="認証コードがありません")

    # .envから読み込んだクライアントシークレットをprint
    print(f"[DEBUG] MICROSOFT_CLIENT_SECRET: {repr(settings.MICROSOFT_CLIENT_SECRET)}")

    token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:8000/api/mail/callback",
        "scope": "offline_access Mail.Read User.Read",
    }
    print(f"[DEBUG] Token request URL: {token_url}")
    print(f"[DEBUG] Token request data: {data}")

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        print(f"[DEBUG] Token response status: {response.status_code}")
        print(f"[DEBUG] Token response body: {response.text}")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"トークン取得失敗: {response.text}")
        token_data = response.json()
        print("Microsoftトークン取得成功:", token_data)
        # 今後はここでDB保存やユーザー紐付けを実装
    return {"message": "認証が完了しました。Discordに戻ってください。"}

@router.get("/api/mail/list")
async def get_mail_list(
    guild_id: str = Query(..., description="DiscordのギルドID"),
    user_id: str = Query(..., description="DiscordのユーザーID"),
    db: AsyncSession = Depends(get_db),
):
    # DBからMailConnectionを検索
    result = await db.execute(
        select(MailConnection).where(
            MailConnection.guild_id == guild_id,
            MailConnection.user_id == user_id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="メール連携情報が見つかりません。/mail-connectで連携してください。")

    access_token = connection.access_token
    url = "https://graph.microsoft.com/v1.0/me/messages"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"メール取得に失敗しました: {response.text}")
        mail_data = response.json()
    return mail_data 