class GenericError(Exception):
    status_code: int
    error_message: str
    error: Exception

    def __init__(
        self,
        status_code: int,
        error_message: str,
        error: Exception = None,
    ) -> None:
        super().__init__()
        self.error = error
        self.status_code = status_code
        self.error_message = error_message
        self.error_detail = {
            "response": None,
            "error": {"errorMessage": self.error_message},
            "status": "failure",
        }

    def __str__(self):
        return f"{self.error_message}"


class DuplicateDataError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=409, error_message=error_message)


class AuthenticationError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=401, error_message=error_message)


class ExternalAPIError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=500, error_message=error_message)


class DatabaseError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=500, error_message=error_message)


class UnprocessableEntityError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=422, error_message=error_message)


class AttributeNotFoundError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=404, error_message=error_message)


class BadRequestError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=400, error_message=error_message)


class PayloadTooLargeError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=413, error_message=error_message)


class LoggingConfigError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=500, error_message=error_message)


class TokenLimitExceededError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=500, error_message=error_message)


class RateLimitError(GenericError):
    def __init__(self, error_message: str):
        super().__init__(status_code=429, error_message=error_message)
