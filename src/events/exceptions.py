from fastapi import HTTPException


class EventError(HTTPException):
    """Base exception for event-related errors"""
    pass


class MainEventError(EventError):
    def __init__(self, error: str):
        super().__init__(status_code=500,
                         detail=f"Failed to create: {error}")
