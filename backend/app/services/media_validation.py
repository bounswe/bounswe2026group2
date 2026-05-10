from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.db.enums import MediaType

MAX_MEDIA_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

ALLOWED_MIME_TYPES = {
    "image": {"image/jpeg", "image/png", "image/webp", "image/gif"},
    "audio": {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/webm"},
    "video": {"video/mp4", "video/webm", "video/quicktime"},
    "document": {
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}

MIME_TYPE_ALIASES = {
    "image/jpg": "image/jpeg",
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/vnd.wave": "audio/wav",
    "audio/x-m4a": "audio/mp4",
    "audio/m4a": "audio/mp4",
    "video/x-m4v": "video/mp4",
    "application/x-pdf": "application/pdf",
}

GENERIC_BINARY_MIME_TYPES = {"application/octet-stream", "binary/octet-stream"}

MIME_TYPE_FALLBACKS_BY_EXTENSION = {
    "image": {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    },
    "audio": {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".webm": "audio/webm",
    },
    "video": {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    },
    "document": {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}


def normalize_media_content_type(file: UploadFile, media_type: MediaType) -> str:
    raw_content_type = (file.content_type or "").split(";")[0].strip().lower()
    normalized_content_type = MIME_TYPE_ALIASES.get(raw_content_type, raw_content_type)

    if normalized_content_type in GENERIC_BINARY_MIME_TYPES:
        extension = Path(file.filename or "").suffix.lower()
        fallback_content_type = MIME_TYPE_FALLBACKS_BY_EXTENSION[media_type.value].get(extension)
        if fallback_content_type:
            return fallback_content_type

    return normalized_content_type


def validate_media_upload(
    file: UploadFile,
    media_type: MediaType,
    *,
    invalid_mime_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type is required",
        )

    allowed_for_type = ALLOWED_MIME_TYPES[media_type.value]
    normalized_content_type = normalize_media_content_type(file, media_type)
    if normalized_content_type not in allowed_for_type:
        raise HTTPException(
            status_code=invalid_mime_status,
            detail=f"Unsupported mime type '{normalized_content_type}' for media type '{media_type.value}'",
        )

    return normalized_content_type


async def read_uploaded_file_content(file: UploadFile) -> bytes:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(file_bytes) > MAX_MEDIA_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_MEDIA_UPLOAD_BYTES} bytes",
        )

    return file_bytes
