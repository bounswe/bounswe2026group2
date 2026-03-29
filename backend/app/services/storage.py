import boto3
from botocore.config import Config

from app.core.config import settings

# Local: points at MinIO (docker-compose).
# Production: points at Supabase Storage S3 endpoint.
# Switch by changing STORAGE_* in .env — no code changes needed.
storage_client = boto3.client(
    "s3",
    endpoint_url=settings.STORAGE_ENDPOINT,
    aws_access_key_id=settings.STORAGE_ACCESS_KEY,
    aws_secret_access_key=settings.STORAGE_SECRET_KEY,
    region_name=settings.STORAGE_REGION,
    config=Config(signature_version="s3v4"),
)


def check_connection() -> None:
    """Verify the storage backend is reachable by listing buckets."""
    storage_client.list_buckets()
