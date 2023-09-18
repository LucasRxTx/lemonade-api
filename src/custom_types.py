from typing import NewType

RawAccessToken = NewType("RawAccessToken", str)


class PasswordPlainText(str):
    """Hide plain text value from accidental logging.

    This is not fool proof, but limits the possibility of
    passwords making it into logs.
    """

    def __init__(self, value: str):
        self.__data = value

    def __new__(cls, _):
        instance = super().__new__(cls, "***")
        return instance

    def get_secret_value(self) -> str:
        """Get the plain text password value."""
        return self.__data


PasswordHashed = NewType("PasswordHashed", str)
