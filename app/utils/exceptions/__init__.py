class EnvironmentFileError(Exception):
    def __init__(self, message):
        self.message = message


class NoParameterError(EnvironmentFileError):
    pass


class InvalidEnvironmentError(EnvironmentFileError):
    pass
