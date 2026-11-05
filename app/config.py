import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
    )

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = "change-me"
    supabase_url: str = ""
    supabase_service_key: str = ""
    database_url: str = ""
    app_base_url: str = "http://localhost:8000"
    dashboard_passcode: str = "1234"
    allowed_telegram_ids: str = ""  # comma-separated; empty = allow all
    storage_bucket: str = "receipts"

    @property
    def allowed_ids(self) -> set[int]:
        if not self.allowed_telegram_ids:
            return set()
        return {int(x) for x in self.allowed_telegram_ids.split(",") if x.strip()}


settings = Settings()
