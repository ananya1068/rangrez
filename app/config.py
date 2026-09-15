import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days, fine for a hackathon demo
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./rangrez.db")
    MOCK_SMS_MODE: bool = os.getenv("MOCK_SMS_MODE", "true").lower() == "true"
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "uploads")


settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
