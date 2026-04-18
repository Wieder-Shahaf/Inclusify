from pydantic import BaseModel
from typing import List, Optional


class UploadResponse(BaseModel):
    filename: str
    content_type: str
    page_count: int
    text_preview: str
    full_text: str
    full_text_length: int
    title: Optional[str] = None
    author: Optional[str] = None
    detected_language: Optional[str] = None
    file_storage_ref: Optional[str] = None
    chunks: Optional[List[str]] = None


class UploadError(BaseModel):
    detail: str
