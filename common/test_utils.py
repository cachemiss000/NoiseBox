"""Defines utils used in unit tests.

This should ideally be tested at some point, likely once we have more than one
function (collect, at time of writing)
"""
import sys
import unittest
from typing import List

from absl import flags

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