import re


class CloseConnectionException(Exception):
    """The client has asked to close the connection."""
    pass


class ClientError(Exception):
    """Close the server because the client misbehaved."""

    def __init__(self, reason: str, *args: str):
        self.reason = reason % args

    def get_safe_close_message(self) -> str:
        """Get a message that can be used safely as the 'close reason' on a client websocket connection."""
        if len(self.reason) < 125:
            return self.reason

        def add_trunc(msg: str) -> str:
            return msg + " <trunc>"

        total_message = ""
        for word in re.findall(r'\S*\s*', self.reason):
            new_msg = "%s %s" % (total_message, word.strip())
            if len(add_trunc(new_msg)) > 125:
                return add_trunc(total_message)
            total_message = new_msg
        assert False, "Should not have been able to iterate through the whole message."
