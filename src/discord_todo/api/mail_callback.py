from fastapi import APIRouter, Request, HTTPException, Depends, Query, Body
import httpx
import os
from src.discord_todo.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.discord_todo.db.session import get_db
from src.discord_todo.models.mail import MailConnection
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import pytz

class MailCallbackRequest(BaseModel):
    code: str
    guild_id: str
    user_id: str

router = APIRouter()

@router.post("/api/mail/callback")
async def mail_callback(
    body: MailCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    code = body.code
    guild_id = body.guild_id
    user_id = body.user_id
    if not code or not guild_id or not user_id:
        raise HTTPException(status_code=400, detail="code, guild_id, user_idは必須です")

    token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:8000/api/mail/callback",
        "scope": "offline_access Mail.Read User.Read",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"トークン取得失敗: {response.text}")
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        if not access_token or not refresh_token or not expires_in:
            raise HTTPException(status_code=500, detail="トークン情報の取得に失敗しました")
        # 有効期限を計算
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        # 有効期限をaware → naive 変換
        if token_expires_at.tzinfo is not None:
            token_expires_at = token_expires_at.replace(tzinfo=None)
        # メールアドレス取得
        headers = {"Authorization": f"Bearer {access_token}"}
        me_resp = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
        if me_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"メールアドレス取得失敗: {me_resp.text}")
        me_data = me_resp.json()
        email = me_data.get("mail") or me_data.get("userPrincipalName")
        if not email:
            raise HTTPException(status_code=500, detail="メールアドレスが取得できませんでした")
    # DB保存（既存があれば更新）
    try:
        result = await db.execute(
            select(MailConnection).where(
                MailConnection.guild_id == guild_id,
                MailConnection.user_id == user_id,
            )
        )
        connection = result.scalar_one_or_none()
        if connection:
            connection.email = email
            connection.access_token = access_token
            connection.refresh_token = refresh_token
            connection.token_expires_at = token_expires_at
        else:
            connection = MailConnection(
                guild_id=guild_id,
                user_id=user_id,
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
            )
            db.add(connection)
        await db.commit()
    except Exception as e:
        print(f"[ERROR] mailconnection保存時に例外発生: {e}")
        raise HTTPException(status_code=500, detail=f"mailconnection保存時に例外発生: {e}")
    return {"message": "認証が完了し、連携情報を保存しました。Discordに戻ってください。"}

@router.get("/api/mail/callback")
async def mail_callback_get(request: Request, db: AsyncSession = Depends(get_db)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="認証コードまたはstateがありません")
    try:
        guild_id, user_id = state.split(":")
    except Exception:
        raise HTTPException(status_code=400, detail="stateの形式が不正です")
    body = MailCallbackRequest(code=code, guild_id=guild_id, user_id=user_id)
    return await mail_callback(body, db)

def to_jst(dt):
    # aware/naive両対応でJSTに変換
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Tokyo')).replace(tzinfo=None)

async def ensure_valid_access_token(connection, db):
    from src.discord_todo.config import settings
    import httpx
    from datetime import datetime, timedelta
    import pytz
    print(f"[DEBUG] トークン有効期限: {to_jst(connection.token_expires_at)}, 現在時刻: {to_jst(datetime.utcnow())}")
    # 期限が5分未満ならリフレッシュ
    if connection.token_expires_at - datetime.utcnow() < timedelta(minutes=5):
        print("[DEBUG] トークン有効期限が近い/切れているためリフレッシュ処理を実行")
        token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
        data = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token,
            "redirect_uri": "http://localhost:8000/api/mail/callback",
            "scope": "offline_access Mail.Read User.Read",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                print(f"[ERROR] トークンリフレッシュ失敗: {response.text}")
                raise HTTPException(status_code=500, detail=f"トークンリフレッシュ失敗: {response.text}")
            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")
            if not access_token or not refresh_token or not expires_in:
                print("[ERROR] トークン情報の取得に失敗しました")
                raise HTTPException(status_code=500, detail="トークン情報の取得に失敗しました")
            connection.access_token = access_token
            connection.refresh_token = refresh_token
            # JSTで保存
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            token_expires_at = to_jst(token_expires_at)
            connection.token_expires_at = token_expires_at
            await db.commit()
            print(f"[DEBUG] トークンをリフレッシュしDBを更新しました。新しい有効期限: {token_expires_at}")
    else:
        print("[DEBUG] トークンはまだ有効です。リフレッシュ不要")
    return connection.access_token

@router.get("/api/mail/list")
async def get_mail_list(
    guild_id: str = Query(..., description="DiscordのギルドID"),
    user_id: str = Query(..., description="DiscordのユーザーID"),
    domain: str = Query(None, description="表示したいメールアドレスのドメイン（例: gmail.com）"),
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

    # アクセストークンの有効期限をチェックし、自動リフレッシュ
    access_token = await ensure_valid_access_token(connection, db)
    url = "https://graph.microsoft.com/v1.0/me/messages"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"メール取得に失敗しました: {response.text}")
        mail_data = response.json()

    # domainでフィルタ
    if domain:
        messages = mail_data.get("value", [])
        messages = [
            m for m in messages
            if m.get("from", {}).get("emailAddress", {}).get("address", "").endswith(f"@{domain}")
        ]
        mail_data["value"] = messages
    return mail_data 