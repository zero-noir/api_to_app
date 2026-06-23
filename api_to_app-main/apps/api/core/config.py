from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'API-to-App Generator API'
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    storage_dir: Path = Path('.data')
    llm_provider: str = 'offline'
    deepseek_api_key: str = ''
    deepseek_model: str = 'deepseek-chat'
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-1.5-flash'
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
