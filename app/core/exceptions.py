from typing import Union, Dict, Any

from fastapi import HTTPException


class APIError(HTTPException):
    """Base API error"""
    def __init__(
        self, 
        status_code: int, 
        detail: Union[str, Dict[str, Any]], 
        headers: dict = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.headers = headers


class AuthenticationError(APIError):
    """Authentication error (401)
    Used for: invalid token, expired token, revoked token etc."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=401, 
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(APIError):
    """Authorization error (403)
    Used for: user has no permission to access specific resource"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=403, detail=detail)


class ValidationError(APIError):
    """Validation error (422)"""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=422, detail=detail)
