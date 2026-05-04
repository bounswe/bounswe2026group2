from urllib.parse import quote

import boto3
from botocore.config import Config

from app.core.config import settings
from app.db.enums import MediaType

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


def get_bucket_for_media_type(media_type: MediaType) -> str:
    if media_type == MediaType.IMAGE:
        return settings.STORAGE_BUCKET_IMAGES
    if media_type == MediaType.AUDIO:
        return settings.STORAGE_BUCKET_AUDIO
    if media_type == MediaType.VIDEO:
        return settings.STORAGE_BUCKET_VIDEOS
    # MVP fallback: documents share the images bucket until a dedicated bucket is added.
    return settings.STORAGE_BUCKET_IMAGES


def upload_bytes(
    *,
    bucket_name: str,
    storage_key: str,
    content: bytes,
    content_type: str,
) -> None:
    storage_client.put_object(
        Bucket=bucket_name,
        Key=storage_key,
        Body=content,
        ContentType=content_type,
    )


def delete_object(*, bucket_name: str, storage_key: str) -> None:
    storage_client.delete_object(Bucket=bucket_name, Key=storage_key)


def build_public_object_url(*, bucket_name: str, storage_key: str) -> str:
    base_url = settings.STORAGE_PUBLIC_URL.rstrip("/")
    encoded_bucket = quote(bucket_name, safe="")
    encoded_key = quote(storage_key.lstrip("/"), safe="/")
    return f"{base_url}/{encoded_bucket}/{encoded_key}"
