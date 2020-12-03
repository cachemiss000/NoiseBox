class CloseConnectionException(Exception):
    """The client has asked to close the connection."""
    pass


class ClientError(Exception):
    """Close the server because the client misbehaved."""
    pass
