import logging


class UserException(Exception):
    """Used to indicate a user error."""
    def __init__(self, user_error_message):
        super().__init__(user_error_message)
        self.user_error_message = user_error_message

    def get_error_message(self) -> str:
        return self.user_error_message


class SystemException(Exception):
    """Used to indicate logical inconsistencies - e.g. bad format in serialized data."""
    pass