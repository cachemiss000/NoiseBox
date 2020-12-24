from typing import Type, Iterable

# Imported for type info.
# Because message_map uses UnsupportedMessageType, we need to use the fully qualified
# type name, using this import style.
import messages.message_map
from common.utils import class_name


class CloseConnectionException(Exception):
    """The client has asked to close the connection."""
    pass


class ClientError(Exception):
    """Close the server because the client misbehaved."""
    pass


class UnsupportedMessageType(Exception):
    def __init__(self, *_argv, routing_cls: "messages.message_map.Types.T_MAP", message_name: str,
                 message: "messages.message_map.Message",
                 expected_message_ti: Iterable[Type["messages.message_map.Types.M_C"]]):
        super().__init__(
            "Routing class '%s' does not support %s type '%s'. Only supports '%s'" % (
                class_name(routing_cls), message_name, message.message_name,
                [class_name(this_msg_t) for this_msg_t in expected_message_ti],), )
        self.found_message = message
        self.expected_message_ti = expected_message_ti
