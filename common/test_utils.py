"""Defines utils used in unit tests.

This should ideally be tested at some point, likely once we have more than one
function (collect, at time of writing)
"""
import sys
import unittest
from typing import List
from unittest.mock import Mock

from absl import flags

import commandserver.server_types.v1_command_types as types
from commandserver.server_types.v1_command_types import ErrorEvent, Message, MessageObj
from commandserver.websocket_muxer import ClientSession
from medialogic import oracles

FLAGS = flags.FLAGS


def collect(oracle: oracles.Oracle) -> List[str]:
    """Get up to 100 songs from the oracle. If you need more there's something wrong with your test."""
    # Grab the starting song
    songs = [oracle.current_song()]
    for i in range(0, 99):
        # Get 99 "next" songs, for a total of 100.
        song = oracle.next_song()
        if song is None:
            return songs
        songs.append(song)
    return songs


def override_flag(key, value):
    """Override a flag key/value pair for a test.

    Works as a context manager with "with" statements to 'unset' changed flags, for individual test cases.
    """

    old_value = FLAGS.__getattr__(key)

    class _OverrideContextManager:
        """Quick and dirty context manager, using scope capture for state management."""

        def __enter__(self):
            yield

        def __exit__(self, *args):
            FLAGS.__setattr__(key, old_value)

    FLAGS.__setattr__(key, value)
    return _OverrideContextManager()


class FlagsTest(unittest.TestCase):
    def setUp(self):
        super(FlagsTest, self).setUp()
        FLAGS(sys.argv)


class MockClient(ClientSession):

    def __init__(self, ws=None):
        if ws is None:
            ws = Mock()
        super().__init__(ws)
        self.sent_messages = []

    async def send(self, message: MessageObj):
        self.sent_messages.append(message.wrap())

    def get_only_message(self) -> Message:
        if len(self.sent_messages) > 1:
            raise ValueError("Too many responses received. Expected 1, got '%s'" % (self.sent_messages,))
        elif not self.sent_messages:
            raise ValueError("Did not receive any messages, when message was expected")

        return self.sent_messages[0]

    def get_error(self) -> ErrorEvent:
        message = self.get_only_message()
        if not message.event or message.event.event_name != ErrorEvent.EVENT_NAME:
            raise ValueError("expected error, but got non-error message: '%s'" % (message,))
        return message.unwrap(ErrorEvent)


def default_song() -> types.Song:
    return types.Song(name="Florgus", description="the florgust-y, blorgust-y beats",
                      metadata={"artist": "florgus-lover", "copyright": "2077"},
                      local_path="C:/florgus/blorgus/vorgus.mp3")


def default_playlist():
    return types.Playlist(name="florgus beats", description="The very best single tune you ever heard",
                          metadata={"timestamp": "2077-01-01", "creator": "TechnoFlorgus"},
                          songs=["Florgus"])


def get_default_event(event_t: types.Type[types.Event]) -> types.Event:
    if event_t == types.PlayStateEvent:
        return types.PlayStateEvent.create(new_play_state=True)
    if event_t == types.SongPlayingEvent:
        return types.SongPlayingEvent.create(current_song=default_song())
    if event_t == types.ListSongsEvent:
        return types.ListSongsEvent.create(songs=[default_song()])
    if event_t == types.ListPlaylistsEvent:
        return types.ListPlaylistsEvent(playlists=[default_playlist()])
    if event_t == types.ErrorEvent:
        return types.ErrorEvent(error_message="Not enough florgus in your tunes",
                                error_type=types.ErrorType.CLIENT_ERROR,
                                error_data="Get more florgus. Nao.",
                                error_env=types.ErrorDataEnv.DEBUG,
                                originating_command=str(get_default_command(types.NextSongCommand)))
    raise ValueError("Couldn't determine default event for event type '%s' =(" % (event_t,))


def get_default_command(command_t: types.Type[types.Command]) -> types.Command:
    if command_t == types.TogglePlayCommand:
        return types.TogglePlayCommand.create(play_state=False)
    if command_t == types.NextSongCommand:
        return types.NextSongCommand.create()
    if command_t == types.ListSongsCommand:
        return types.ListSongsCommand.create()
    if command_t == types.ListPlaylistsCommand:
        return types.ListPlaylistsCommand.create()
    raise ValueError("Couldn't determine default command for command type '%s' =(" % (command_t,))
