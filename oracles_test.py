import itertools
import unittest
from typing import List

import oracles


def collect(oracle: oracles.Oracle) -> List[str]:
    """Get up to 100 songs from the oracle. If you need more there's something wrong with your test."""
    songs = []
    for i in range(0, 100):
        song = oracle.next_song()
        if song is None:
            return songs
        songs.append(song)
    return songs


class PlaylistTest(unittest.TestCase):

    def test_basic_functionality(self):
        songs = ["1", "2", "3"]
        o = oracles.PlaylistOracle(songs)
        self.assertListEqual(collect(o), songs)
        self.assertIsNone(o.next_song())

    def test_empty_list(self):
        self.assertIsNone(oracles.PlaylistOracle(None).next_song())
        self.assertIsNone(oracles.PlaylistOracle([]).next_song())

    def test_abuse(self):
        o = oracles.PlaylistOracle(["1"])
        o.next_song()
        for _ in range(0, 5000):
            self.assertIsNone(o.next_song())


class ChainTest(unittest.TestCase):

    def test_two_oracles(self):
        songs = ["1", "2", "3", "4", "5", "6"]

        p1 = oracles.PlaylistOracle(songs[:2])
        p2 = oracles.PlaylistOracle(songs[2:])

        o = oracles.ChainOracle()
        o.add(p1)
        o.add(p2)

        self.assertListEqual(collect(o), songs)

    def test_finish_list_then_continue(self):
        songs1 = ["1", "2", "3", "4"]
        songs2 = ["5", "4", "3", "2"]

        p1 = oracles.PlaylistOracle(songs1)
        p2 = oracles.PlaylistOracle(songs2)

        o = oracles.ChainOracle()

        o.add(p1)
        collected1 = collect(o)

        o.add(p2)
        collected2 = collect(o)

        self.assertListEqual(collected1, songs1)
        self.assertListEqual(collected2, songs2)

    def test_add_halfway_through(self):
        songs1 = ["1", "2", "3", "4"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["5", "6", "7"]
        p2 = oracles.PlaylistOracle(songs2)
        o = oracles.ChainOracle()

        o.add(p1)
        collected = [o.next_song(), o.next_song()]
        o.add(p2)
        collected.extend(collect(o))

        self.assertListEqual(collected, songs1 + songs2)

    def test_add_empties(self):
        songs = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs)
        o = oracles.ChainOracle()
        o.add(None)
        o.add(oracles.PlaylistOracle([]))
        o.add(p1)

        self.assertListEqual(collect(o), songs)

    def test_empty_start(self):
        songs = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs)
        p2 = oracles.PlaylistOracle(songs)

        o = oracles.ChainOracle()
        song0 = o.next_song()
        o.add(p1)
        o.add(p2)

        self.assertIsNone(song0)
        self.assertListEqual(collect(o), songs * 2)


class TestSwitchOracle(unittest.TestCase):

    def test_no_oracle(self):
        o = oracles.SwitchOracle()
        self.assertIsNone(o.next_song())

    def test_add_oracle(self):
        songs = ["1", "2", "3"]
        o = oracles.SwitchOracle()
        p1 = oracles.PlaylistOracle(songs)

        o.next_song()
        o.set_oracle(p1)

        self.assertListEqual(collect(o), songs)

    def test_set_to_none(self):
        songs = ["1", "2", "3"]
        o = oracles.SwitchOracle()
        p1 = oracles.PlaylistOracle(songs)

        # Only get 2 songs so that we can make sure the third *isn't* collected when we switch.
        o.set_oracle(p1)
        collected = [o.next_song(), o.next_song()]
        o.set_oracle(None)

        self.assertIsNone(o.next_song())
        self.assertListEqual(collected, songs[:2])

    def test_set_to_another(self):
        o = oracles.SwitchOracle()
        songs1 = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["4", "5", "6"]
        p2 = oracles.PlaylistOracle(songs2)
        songs3 = ["7", "8", "9"]
        p3 = oracles.PlaylistOracle(songs3)

        o.set_oracle(p1)
        collected = [o.next_song(), o.next_song()]
        o.set_oracle(p2)
        collected.extend([o.next_song(), o.next_song(), o.next_song(), o.next_song()])
        o.set_oracle(p3)
        collected.extend([o.next_song(), o.next_song(), o.next_song()])

        self.assertListEqual(collected, list(itertools.chain(songs1[:2], songs2, [None], songs3)))


class InterruptOracleTest(unittest.TestCase):

    def test_default_behavior(self):
        songs = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs)
        o = oracles.InterruptOracle(p1)

        self.assertListEqual(collect(o), songs)

    def test_interrupt_before_finish(self):
        songs1 = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["4", "5", "6"]
        p2 = oracles.PlaylistOracle(songs2)
        o = oracles.InterruptOracle(p1)

        collected = [o.next_song(), o.next_song()]
        o.interrupt(p2)
        collected.extend(collect(o))

        self.assertListEqual(collected, ["1", "2", "4", "5", "6", "3"])

    def test_interrupt_after_finish(self):
        songs1 = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["4", "5", "6"]
        p2 = oracles.PlaylistOracle(songs2)
        o = oracles.InterruptOracle(p1)

        collected = collect(o)
        o.interrupt(p2)
        collected.extend(collect(p2))

        self.assertListEqual(collected, songs1 + songs2)

    def test_no_default(self):
        songs = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs)
        o = oracles.InterruptOracle(None)

        collected = [o.next_song()]
        o.interrupt(p1)
        collected.extend(collect(o))

        expected = list([None])
        expected.extend(songs)
        self.assertListEqual(collected, expected)


if __name__ == '__main__':
    unittest.main()
