from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    master_tg_id: int
    tz: str = "Europe/Moscow"
    db_url: str = "sqlite+aiosqlite:///./data/bot.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()