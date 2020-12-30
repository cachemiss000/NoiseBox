import collections
import logging
from typing import Optional, Callable, Any, cast, List

from absl import flags
from pydantic import ValidationError
from typing_extensions import Coroutine

import commandserver.server_types.v1_command_types as c_types
from commandserver import websocket_muxer
from commandserver.websocket_muxer import ClientSession
from common import utils
from common.utils import class_name
from medialogic import media_library, controller

VERSION = "V1"
FLAGS = flags.FLAGS

# TODO: For type sanity, this NEEDS to be a class. Goddamn.
Page = collections.namedtuple("Page", ["list_hash", "element"])


class OutdatedPageException(Exception):
    pass


def add_error_handling(awaitable_do_fn: Callable[[Any, str, ClientSession], Coroutine]):
    async def accept_func(self, command_str: str, client_session: ClientSession):
        err: Optional[c_types.ErrorEvent] = None
        try:
            await awaitable_do_fn(self, command_str, client_session)
        except c_types.EventException as e:
            err = e.error_event
        except ValidationError as e:
            err = c_types.ErrorEvent.create(
                error_type=c_types.ErrorType.INTERNAL_ERROR,  # client validation errors are caught elsewhere.
                error_message=utils.simplify_validation_error(e),
                error_data=str(e),
                error_env=c_types.ErrorDataEnv.DEBUG,
                originating_command=command_str)
        except Exception as e:
            err = c_types.ErrorEvent.create(
                error_type=c_types.ErrorType.INTERNAL_ERROR,
                error_message="Unexpected error encountered: '%s'" % (e,),
                error_env=c_types.ErrorDataEnv.DEBUG,
                error_data=str(e),
                originating_command=command_str if command_str else None)

        if not err:
            return
        if not FLAGS.debug:
            err = err.for_prod()
        await client_session.send(err)

    return accept_func


class MediaServer(websocket_muxer.Server):
    def __init__(self, c: controller.Controller, ml: media_library.MediaLibrary):
        super(MediaServer, self).__init__()
        self.media_library = ml
        self.controller = c

    @add_error_handling
    async def accept(self, command_str: str, client_session: ClientSession):
        try:
            message = c_types.Message.parse_raw(command_str)
        except ValidationError as e:
            raise c_types.ErrorEvent.create(
                error_type=c_types.ErrorType.CLIENT_ERROR,
                error_message=utils.simplify_validation_error(e),
                error_data=str(e),
                error_env=c_types.ErrorDataEnv.DEBUG,
                originating_command=command_str).exception()
        if message.event:
            self.handle_event(message.event)
        if message.command:
            return_event = self.handle_command(message.command)
            await client_session.send(return_event.wrap())

    def toggle_play(self, play_request: c_types.TogglePlayCommand) -> c_types.Event:
        """Toggles the play/pause state, with "play" == True.

        This contrasts with VLC's interpretation, where "pause" == True, which is standard further down
        the stack.
        """
        if play_request is None or play_request.play_state is None:
            self.controller.toggle_pause()
            return c_types.PlayStateEvent.create(new_play_state=self.controller.playing())

        # Invert play_state because we're setting the pause value.
        # Vlc has some weird semantics. I refuse to build around them at this level.
        self.controller.set_pause(not play_request.play_state)

        return c_types.PlayStateEvent.create(new_play_state=self.controller.playing())

    def next_song(self, next_song_command: c_types.NextSongCommand) -> c_types.Event:
        raise NotImplementedError('still need to do this =/')

    def list_playlists(self, _list_playlist_command: c_types.ListPlaylistsCommand) -> c_types.Event:
        playlists: List[c_types.Playlist] = []
        for playlist in self.media_library.list_playlists():
            playlists.append(c_types.Playlist(name=playlist[0], songs=playlist[1]))
        return c_types.ListPlaylistsEvent.create(playlists=playlists)

    @staticmethod
    def error_event(error_event: c_types.ErrorEvent):
        logging.error(error_event)

    def handle_command(self, command: c_types.Command) -> c_types.Event:
        if command.command_name == c_types.TogglePlayCommand.COMMAND_NAME:
            return self.toggle_play(cast(c_types.TogglePlayCommand, command))
        if command.command_name == c_types.NextSongCommand.COMMAND_NAME:
            return self.next_song(cast(c_types.NextSongCommand, command))
        if command.command_name == c_types.ListPlaylistsCommand.COMMAND_NAME:
            return self.list_playlists(cast(c_types.ListPlaylistsCommand, command))
        raise NotImplementedError("Command type %s not implemented" % (class_name(command),))

    def handle_event(self, event: c_types.Event):
        if event.event_name == c_types.ErrorEvent.EVENT_NAME:
            return self.error_event(cast(c_types.ErrorEvent, event))
        raise NotImplementedError("Event type %s not implemented" % (class_name(event),))
