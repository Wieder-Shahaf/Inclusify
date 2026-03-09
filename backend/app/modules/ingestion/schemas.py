from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response model for successful PDF upload."""
    filename: str
    content_type: str
    page_count: int
    text_preview: str
    full_text: str
    full_text_length: int


class UploadError(BaseModel):
    """Response model for upload errors."""
    detail: str
