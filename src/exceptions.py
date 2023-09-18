class UnprocessableEntityError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class ServerError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class StandAlreadyExistsError(Exception):
    pass


class InvalidPermissionsError(Exception):
    pass


class NotFound(Exception):
    pass
