from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    NEWSAPI_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "sentiment-app/0.1"
    OPENAI_API_KEY: str = ""
    WINDOW_HOURS: int = 48
    PORT: int = 8000

settings = Settings(_env_file=".env", _env_file_encoding="utf-8")