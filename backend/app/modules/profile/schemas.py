from pydantic import BaseModel
from typing import Optional


class ProfileRead(BaseModel):
    full_name: Optional[str] = None
    profession: Optional[str] = None
    institution: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    profession: Optional[str] = None
    institution: Optional[str] = None
