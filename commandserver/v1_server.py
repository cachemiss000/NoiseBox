import collections
from typing import List, Optional, Callable, Any

from absl import flags
from typing_extensions import Coroutine

import commandserver.server_types.v1_command_types as c_types
from commandserver import websocket_muxer
from commandserver.server_exceptions import UnsupportedMessageType
from commandserver.websocket_muxer import ClientSession
from medialogic import media_library, controller

VERSION = "V1"
FLAGS = flags.FLAGS

# TODO: For type sanity, this NEEDS to be a class. Goddamn.
Page = collections.namedtuple("Page", ["list_hash", "element"])


class OutdatedPageException(Exception):
    pass


def event(event_cls: c_types.EventCls):
    return c_types.Event(message_name=event_cls.MESSAGE_NAME,
                         payload=event_cls)


# Command names in this list do not need a parameter list to execute successfully, and will
# not be checked for them by the command validation code.
PARAMETERLESS_COMMANDS: List[str] = [
    c_types.TogglePlayCommand.MESSAGE_NAME,
    c_types.NextSongCommand.MESSAGE_NAME,
    c_types.ListSongsCommand.MESSAGE_NAME,
    c_types.ListPlaylistsCommand.MESSAGE_NAME,
]


def add_error_handling(awaitable_do_fn: Callable[[Any, str, ClientSession], Coroutine]):
    async def accept_func(self, command_str: str, client_session: ClientSession):
        err: Optional[c_types.ErrorEvent] = None
        try:
            await awaitable_do_fn(self, command_str, client_session)
        except c_types.ErrorEvent as e:
            err = e
        except Exception as e:
            err = c_types.ErrorEvent(
                error_type=c_types.ErrorType.INTERNAL_ERROR,
                error_message="Unexpected error encountered: '%s'" % (e,),
                error_env=c_types.ErrorDataEnv.DEBUG,
                error_data=str(e),
                originating_command=command_str if command_str else None)

        if not err:
            return
        if not FLAGS.debug:
            err = err.for_prod()
        await client_session.send(err.wrap())
    return accept_func


class MediaServer(websocket_muxer.Server, c_types.CommandTypeMap):
    def __init__(self, c: controller.Controller, ml: media_library.MediaLibrary):
        super(MediaServer, self).__init__()
        self.media_library = ml
        self.controller = c

    @add_error_handling
    async def accept(self, command_str: str, client_session: ClientSession):
        try:
            command = MediaServer.parse_command(command_str)
            return_event = self.handle_message(command)
            await client_session.send(return_event.wrap())
        except UnsupportedMessageType as e:
            raise c_types.ErrorEvent(
                error_type=c_types.ErrorType.CLIENT_ERROR,
                error_message="Command name '%s' is not a valid %s command" % (
                    e.found_message.message_name, VERSION),
                error_data=str(e),
                error_env=c_types.ErrorDataEnv.DEBUG,
                originating_command=command_str)

    @classmethod
    def parse_command(cls, command: str) -> c_types.Command:
        """Parses a JSON command from the input string as expected over a raw websocket."""
        # infer_missing returns missing fields as None, which is always the desired behavior
        # in our case. Otherwise, empty optional fields would throw.
        command_result = c_types.Command.from_json(command, infer_missing=True)
        if command_result.message_name is None:
            raise c_types.ErrorEvent(error_type=c_types.ErrorType.CLIENT_ERROR,
                                     error_message="Command name must be specified on the input command",
                                     error_data=command,
                                     error_env=c_types.ErrorDataEnv.DEBUG,
                                     originating_command=command)

        if command_result.message_name in PARAMETERLESS_COMMANDS:
            return command_result  # No error checking needed if it otherwise parsed correctly.

        if command_result.payload is None:
            raise c_types.ErrorEvent(error_type=c_types.ErrorType.CLIENT_ERROR,
                                     error_message="Payload expected for command '%s'" % (command_result.message_name,),
                                     error_data=command,
                                     error_env=c_types.ErrorDataEnv.DEBUG,
                                     originating_command=command)
        return command_result

    def with_toggle_play(self, play_request: Optional[c_types.TogglePlayCommand]) -> c_types.Event:
        """Toggles the play/pause state, with "play" == True.

        This contrasts with VLC's interpretation, where "pause" == True, which is standard further down
        the stack.
        """
        if play_request is None or play_request.play_state is None:
            self.controller.toggle_pause()
            return event(c_types.PlayStateEvent(new_play_state=self.controller.playing()))

        # Invert play_state because we're setting the pause value.
        # Vlc has some weird semantics. I refuse to build around them at this level.
        self.controller.set_pause(not play_request.play_state)

        return event(c_types.PlayStateEvent(new_play_state=self.controller.playing()))
