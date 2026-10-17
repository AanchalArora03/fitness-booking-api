class EmailAlreadyRegisteredError(Exception):
    """Raised when signup uses an email belonging to an existing account."""

    def __init__(self) -> None:
        super().__init__("An account with this email already exists.")


class InvalidCredentialsError(Exception):
    """Raised for both unknown accounts and incorrect passwords."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password.")


class ClassNotFoundError(Exception):
    pass


class BookingConflictError(Exception):
    pass
