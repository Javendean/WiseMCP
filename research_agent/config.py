from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application configuration using Pydantic BaseSettings.
    Loads settings from a .env file and environment variables.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    GITHUB_TOKEN: str = "YOUR_GITHUB_TOKEN_HERE"
    LOCAL_CODEBASE_PATH: str = "."

settings = Settings()
