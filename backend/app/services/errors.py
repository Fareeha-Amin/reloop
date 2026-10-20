"""Service-layer errors. app.main maps each to an HTTP status in one place."""


class ServiceError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFound(ServiceError):
    """Missing, or not visible to this user. The two are deliberately indistinguishable."""

    status_code = 404


class Conflict(ServiceError):
    """Valid request, but it clashes with current state (duplicate, wrong status, ...)."""

    status_code = 409


class Unprocessable(ServiceError):
    status_code = 422
