"""Defines utils used in unit tests.

This should ideally be tested at some point, likely once we have more than one
function (collect, at time of writing)
"""
import sys
import unittest
from typing import List, Union
from unittest.mock import Mock

from absl import flags

from commandserver.server_types.v1_command_types import ErrorEvent
from commandserver.websocket_muxer import ClientSession
from medialogic import oracles
from messages.message_map import Message, MessageCls

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

    async def send(self, message: Union[Message, MessageCls]):
        self.sent_messages.append(message.wrap())

    def get_only_message(self) -> Message:
        if len(self.sent_messages) > 1:
            raise ValueError("Too many responses received. Expected 1, got '%s'" % (self.sent_messages,))
        elif not self.sent_messages:
            raise ValueError("Did not receive any messages, when message was expected")

        return self.sent_messages[0]

    def get_error(self) -> ErrorEvent:
        message = self.get_only_message()
        if message.message_name != ErrorEvent.MESSAGE_NAME:
            raise ValueError("expected error, but got non-error message: '%s'" % (message,))
        return message.unwrap(ErrorEvent)