from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    # Set to "true" in .env to write every SQL query to logs/sql.log
    LOG_SQL: bool = False

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "your-secret-key"  # Change this in production!
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # ── Object Storage (S3-compatible) ────────────────────────────────────────
    # Local: points at MinIO.  Production: points at Supabase Storage S3 endpoint.
    STORAGE_ENDPOINT: str = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_REGION: str = "us-east-1"
    # Public base URL used to build direct links for public buckets.
    # For MinIO local it's the same as STORAGE_ENDPOINT.
    # For Supabase set this to https://<project>.supabase.co/storage/v1/object/public
    STORAGE_PUBLIC_URL: str = "http://localhost:9000"

    # Bucket names (must match what you created in MinIO / Supabase Storage)
    STORAGE_BUCKET_IMAGES: str = "images"
    STORAGE_BUCKET_AUDIO: str = "audio"
    STORAGE_BUCKET_VIDEOS: str = "videos"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
