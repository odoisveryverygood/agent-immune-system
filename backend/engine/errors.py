class EngineError(Exception):
    """Public error codes/messages must not contain raw provider bodies or secrets."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.public_message = message
        super().__init__(message)


class BudgetStopped(EngineError):
    pass


class IntegrationError(EngineError):
    pass
