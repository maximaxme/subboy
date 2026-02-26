from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    DATABASE_URL: str
    JWT_SECRET: str = ""  # для API subboy; если пусто — используется BOT_TOKEN
    WEB_ORIGIN: str = "http://localhost:5173"  # откуда разрешён запрос к API (CORS)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()
