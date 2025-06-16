from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定"""

    # 環境設定
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # Discord設定
    DISCORD_TOKEN: str
    DISCORD_CLIENT_ID: str | None = None
    DISCORD_CLIENT_SECRET: str | None = None
    DISCORD_DEVELOPMENT_GUILD_ID: str | None = None

    # データベース設定
    DATABASE_URL: str

    # Microsoft Graph API設定
    MICROSOFT_CLIENT_ID: str = "00013887-1d74-406e-896c-00eb0647fb9a"  # RITS_TASK_BOT
    MICROSOFT_CLIENT_SECRET: str  # アプリケーションのシークレット
    # 個人用Microsoftアカウント対応のため"common"テナントを使用
    MICROSOFT_TENANT_ID: str = "common"  # 個人・組織アカウント両対応

    # FastAPI設定
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # セキュリティ設定
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings() 