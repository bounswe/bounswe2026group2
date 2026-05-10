from pydantic import BaseModel


class TranscriptionPreviewResponse(BaseModel):
    transcript: str | None
