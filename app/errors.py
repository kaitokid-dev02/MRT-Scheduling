"""Application-level exceptions.

Domain and service code raises these; the HTTP layer (``app/__init__.py``)
translates them into JSON or HTML responses. Nothing in here knows about Flask.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base class for expected, user-facing errors."""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(DomainError):
    status_code = 400


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    """The request is valid but the resource is in the wrong state."""

    status_code = 409


class RouteNotFoundError(DomainError):
    """Both stations exist but no path connects them."""

    status_code = 422
