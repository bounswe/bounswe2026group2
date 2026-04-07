import uuid
from io import BytesIO

from starlette.datastructures import Headers, UploadFile

from app.db.enums import MediaType
from app.db.media_file import MediaFile

# Minimal valid PNG (67-byte 1×1 pixel) — small enough to be fast,
# valid enough to pass content-type checks in the upload flow.
_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

DEFAULT_FILENAME = "test_photo.png"
DEFAULT_CONTENT_TYPE = "image/png"
DEFAULT_BUCKET_NAME = "images"
DEFAULT_STORAGE_KEY_PREFIX = "stories"


def make_upload_file(
    *,
    filename: str = DEFAULT_FILENAME,
    content: bytes = _MINIMAL_PNG,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> UploadFile:
    """Return an in-memory UploadFile for use in service-level unit tests.

    No real file or cloud storage is involved — the content lives entirely
    in a BytesIO buffer, so tests stay fast and isolated.
    """
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def make_media_file_entity(
    *,
    story_id: uuid.UUID,
    bucket_name: str = DEFAULT_BUCKET_NAME,
    storage_key: str | None = None,
    original_filename: str = DEFAULT_FILENAME,
    mime_type: str = DEFAULT_CONTENT_TYPE,
    media_type: MediaType = MediaType.IMAGE,
    file_size_bytes: int = len(_MINIMAL_PNG),
    sort_order: int = 0,
    alt_text: str | None = None,
    caption: str | None = None,
) -> MediaFile:
    """Return a MediaFile ORM object for direct insertion into a test DB session."""
    if storage_key is None:
        storage_key = f"{DEFAULT_STORAGE_KEY_PREFIX}/{story_id}/media/{uuid.uuid4()}.png"
    return MediaFile(
        story_id=story_id,
        bucket_name=bucket_name,
        storage_key=storage_key,
        original_filename=original_filename,
        mime_type=mime_type,
        media_type=media_type,
        file_size_bytes=file_size_bytes,
        sort_order=sort_order,
        alt_text=alt_text,
        caption=caption,
    )
