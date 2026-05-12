from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.deps import get_current_user
from app.db.user import User
from app.models.transcription import TranscriptionPreviewResponse
from app.services.transcription_service import preview_audio_transcription

router = APIRouter(prefix="/transcription", tags=["transcription"])


@router.post(
    "/preview",
    response_model=TranscriptionPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview an audio transcript",
    description=(
        "Transcribe an uploaded audio file without persisting media metadata or requiring a story id. "
        "Requires authentication."
    ),
    responses={
        400: {"description": "Empty or invalid file"},
        401: {"description": "Missing or invalid authentication token"},
        413: {"description": "File exceeds the 20 MB size limit"},
    },
)
async def preview_transcription(
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_user),
):
    transcript = await preview_audio_transcription(file)
    return TranscriptionPreviewResponse(transcript=transcript)
