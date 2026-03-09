"""
Pydantic schemas for user authentication.

Uses FastAPI Users base schemas with custom validation rules:
- Email validation via email-validator
- Password minimum 8 characters
"""
import uuid
from typing import Optional

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data (API responses)."""

    role: str = "user"


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user.

    Validation:
    - email: Must be valid email format (inherited from BaseUserCreate)
    - password: Minimum 8 characters
    """

    password: str  # Will be validated by field_validator

    def __init__(self, **data):
        # Validate password length before parent init
        if "password" in data and len(data["password"]) < 8:
            from pydantic import ValidationError
            from pydantic_core import InitErrorDetails, PydanticCustomError

            raise ValidationError.from_exception_data(
                "UserCreate",
                [
                    InitErrorDetails(
                        type=PydanticCustomError(
                            "string_too_short",
                            "String should have at least 8 characters",
                        ),
                        loc=("password",),
                        input=data["password"],
                    )
                ],
            )
        super().__init__(**data)


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data."""

    role: Optional[str] = None
