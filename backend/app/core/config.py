from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://fams:fams123@localhost:5432/fams"
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    RECOGNITION_THRESHOLD: float = 0.45   # nguong cosine de nhan dien
    DUPLICATE_THRESHOLD: float = 0.60     # nguong canh bao trung khi enrollment
    LATE_AFTER_MINUTES: int = 15          # sau X phut tinh la muon
    EVIDENCE_DIR: str = "./evidence"
    EVIDENCE_RETENTION_DAYS: int = 90     # anh bang chung qua han bi xoa tu dong
    CORS_ORIGINS: str = "http://localhost:5173"  # phan cach boi dau phay

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
