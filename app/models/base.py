"""Base model utilities."""

from typing import Any
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom Pydantic type for MongoDB ObjectId."""

    @classmethod
    def __get_validators__(cls):
        """Pydantic validator."""
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, info: Any) -> ObjectId:
        """Validate ObjectId."""
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema: dict) -> None:
        """JSON schema for ObjectId."""
        field_schema.update(type="string")
