from typing import Any


class BaseAppException(Exception):
    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        self.message = message
        self.payload = payload or {}

    @property
    def status_code(self) -> int:
        return 500

    @property
    def error_code(self) -> str:
        return "INTERNAL_APP_ERROR"


class NotFoundException(BaseAppException):
    @property
    def status_code(self) -> int:
        return 404

    @property
    def error_code(self) -> str:
        return "NOT_FOUND"


class DuplicationException(BaseAppException):
    @property
    def status_code(self) -> int:
        return 409

    @property
    def error_code(self) -> str:
        return "DUPLICATED_ENTITY"


class BusinessLogicException(BaseAppException):
    @property
    def status_code(self) -> int:
        return 400

    @property
    def error_code(self) -> str:
        return "BAD_REQUEST"
