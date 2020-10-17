import itertools
import unittest
from typing import List

import oracles


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


class PlaylistTest(unittest.TestCase):

    def test_basic_functionality(self):
        songs = ["1", "2", "3"]
        o = oracles.PlaylistOracle(songs)
        self.assertListEqual(collect(o), songs)
        self.assertIsNone(o.next_song())

    def test_empty_list(self):
        self.assertIsNone(oracles.PlaylistOracle(None).current_song())
        self.assertIsNone(oracles.PlaylistOracle(None).next_song())

        self.assertIsNone(oracles.PlaylistOracle([]).current_song())
        self.assertIsNone(oracles.PlaylistOracle([]).next_song())

    def test_abuse(self):
        o = oracles.PlaylistOracle(["1"])
        self.assertEqual(o.current_song(), "1")
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
        # Chop off the memoized None at the beginning.
        self.assertListEqual(collected2[1:], songs2)

    def test_add_halfway_through(self):
        songs1 = ["1", "2", "3", "4"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["5", "6", "7"]
        p2 = oracles.PlaylistOracle(songs2)
        o = oracles.ChainOracle()

        o.add(p1)
        collected = [o.current_song(), o.next_song()]
        o.add(p2)

        # Shave the first entry off "collect" since we already got it.
        collected.extend(collect(o)[1:])

        self.assertListEqual(collected, songs1 + songs2)

    def test_add_empties(self):
        songs = ["1", "2", "3"]
        o = oracles.ChainOracle()
        o.add(None)
        o.add(oracles.PlaylistOracle([]))
        o.add(oracles.PlaylistOracle(songs))

        self.assertIsNone(o.current_song())
        # Chop off the "None" from the start because of the first "current_song" call.
        self.assertListEqual(collect(o)[1:], songs)

    def test_empty_start(self):
        songs = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs)
        p2 = oracles.PlaylistOracle(songs)

        o = oracles.ChainOracle()
        song0 = o.current_song()
        song1 = o.next_song()
        o.add(p1)
        o.add(p2)
        collected = collect(o)

        self.assertIsNone(song0)
        self.assertIsNone(song1)
        # Chop off the memoized "None" at the beginning.
        self.assertListEqual(collected[1:], songs * 2)

    def test_clear(self):
        songs1 = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["4", "5", "6"]
        p2 = oracles.PlaylistOracle(songs2)

        # Add p1, only collect the first two, clear,
        # collect 2 of p2, then clear again and collect one last song.
        o = oracles.ChainOracle()
        o.add(p1)
        collected = [o.current_song(), o.next_song()]
        o.clear()
        o.add(p2)
        collected.extend([o.next_song(), o.next_song()])
        o.clear()
        collected.append(o.next_song())

        self.assertListEqual(collected, ["1", "2", "4", "5", None])

    def test_none_returning_current_song_sticks(self):
        songs = ["1", "2", "3"]
        p = oracles.PlaylistOracle(songs)
        o = oracles.ChainOracle()

        no_song_available_rv = o.current_song()
        o.add(p)
        memoized_to_none_rv = o.current_song()
        next_song_rv = o.next_song()

        self.assertIsNone(no_song_available_rv)
        self.assertIsNone(memoized_to_none_rv)
        self.assertEqual(next_song_rv, "1")

    def test_none_after_finishing_chain_sticks(self):
        songs = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs)
        p2 = oracles.PlaylistOracle(songs)
        o = oracles.ChainOracle()

        o.add(p1)
        collected = collect(o)

        no_songs_available_rv = o.next_song()
        o.add(p2)
        memoized_to_none_rv = o.current_song()
        start_next_list_rv = o.next_song()

        self.assertEqual(collected, songs)
        self.assertIsNone(no_songs_available_rv)
        self.assertIsNone(memoized_to_none_rv)
        self.assertEqual(start_next_list_rv, "1")

    def test_clearing_oracles_memoizes_last_song(self):
        songs1 = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["4", "5"]
        p2 = oracles.PlaylistOracle(songs2)
        o = oracles.ChainOracle()

        o.add(p1)
        first_song_rv = o.current_song()
        o.clear()
        memoized_first_song_rv = o.current_song()
        empty_next_song_rv = o.next_song()
        still_empty_current_song_rv = o.next_song()

        o.add(p2)
        # This should be the second song since "p" maintains its state even after being cleared.
        second_song_rv = o.next_song()

        self.assertEqual(first_song_rv, "1")
        self.assertEqual(memoized_first_song_rv, "1")
        self.assertIsNone(empty_next_song_rv)
        self.assertIsNone(still_empty_current_song_rv)
        self.assertEqual(second_song_rv, "4")

    def test_immediate_next_song_returns_second_normally(self):
        songs = ["1", "2"]
        p = oracles.PlaylistOracle(songs)
        o = oracles.ChainOracle()

        o.add(p)

        self.assertEqual(o.next_song(), "2")

    def test_adding_after_memoizing_none_plays_first_song_before_adding_other_oracles(self):
        songs = ["1"]
        p = oracles.PlaylistOracle(songs)
        o = oracles.ChainOracle()

        memoizing_none_rv = o.current_song()
        o.add(p)
        still_memoized_none_rv = o.current_song()
        first_song_of_new_oracle_rv = o.next_song()

        self.assertIsNone(memoizing_none_rv)
        self.assertIsNone(still_memoized_none_rv)
        self.assertEqual(first_song_of_new_oracle_rv, "1")

    def test_adding_after_memoizing_none_plays_first_song_after_adding_other_oracles(self):
        songs1 = ["1"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["2"]
        p2 = oracles.PlaylistOracle(songs2)
        o = oracles.ChainOracle()

        o.add(p1)
        first_song_rv = o.current_song()
        off_the_end_rv = o.next_song()
        o.add(p2)
        memoized_off_the_end_rv = o.current_song()
        second_song_rv = o.next_song()

        self.assertEqual(first_song_rv, "1")
        self.assertIsNone(off_the_end_rv)
        self.assertIsNone(memoized_off_the_end_rv)
        self.assertEqual(second_song_rv, "2")


class SwitchOracleTest(unittest.TestCase):

    def test_no_oracle(self):
        o = oracles.SwitchOracle()
        self.assertIsNone(o.next_song())

    def test_add_oracle(self):
        songs = ["1", "2", "3"]
        o = oracles.SwitchOracle()
        p1 = oracles.PlaylistOracle(songs)

        no_song_available_rv = o.current_song()
        o.set_oracle(p1)

        self.assertIsNone(no_song_available_rv)
        # Collect will return "None" first because we've memoized
        # "None" above, and collect calls "current_song()" first.
        self.assertListEqual(collect(o), [None] + songs)

    def test_set_to_none(self):
        songs = ["1", "2", "3"]
        o = oracles.SwitchOracle()
        p1 = oracles.PlaylistOracle(songs)

        # Only get 2 songs so that we can make sure the third *isn't* collected when we switch.
        o.set_oracle(p1)
        collected = [o.current_song(), o.next_song()]
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
        collected = [o.current_song(), o.next_song()]
        o.set_oracle(p2)
        collected.extend([o.next_song(), o.next_song(), o.next_song(), o.next_song()])
        o.set_oracle(p3)
        collected.extend([o.next_song(), o.next_song(), o.next_song()])

        self.assertListEqual(collected, list(itertools.chain(songs1[:2], songs2, [None], songs3)))

    def test_memoize_to_none_and_play_first_with_current_song_before_setting(self):
        songs = ["1", "2"]
        p = oracles.PlaylistOracle(songs)
        o = oracles.SwitchOracle()

        no_songs_set_rv = o.current_song()
        o.set_oracle(p)
        memoized_to_none_rv = o.current_song()
        first_song_of_playlist_rv = o.next_song()

        self.assertIsNone(no_songs_set_rv)
        self.assertIsNone(memoized_to_none_rv)
        self.assertEqual(first_song_of_playlist_rv, "1")

    def test_go_to_second_song_without_memoizing_call_to_current_song(self):
        songs = ["1", "2"]
        p = oracles.PlaylistOracle(songs)
        o = oracles.SwitchOracle()

        o.set_oracle(p)

        self.assertEqual(o.next_song(), "2")

    def test_memoize_old_oracles_after_switching(self):
        songs1 = ["1"]
        p1 = oracles.PlaylistOracle(songs1)
        songs2 = ["2"]
        p2 = oracles.PlaylistOracle(songs2)
        o = oracles.SwitchOracle()

        o.set_oracle(p1)
        first_song_on_p1_rv = o.current_song()
        o.set_oracle(p2)
        memoized_first_song_from_p1_rv = o.current_song()
        new_first_song_from_p2_rv = o.next_song()

        self.assertEqual(first_song_on_p1_rv, "1")
        self.assertEqual(memoized_first_song_from_p1_rv, "1")
        self.assertEqual(new_first_song_from_p2_rv, "2")


    def test_memoizing_null(self):
        songs1 = ["1"]
        p1 = oracles.PlaylistOracle(songs1)
        o = oracles.SwitchOracle()

        o.set_oracle(None)
        none_song = o.current_song()
        o.set_oracle(p1)
        songs_collected = collect(o)

        self.assertIsNone(none_song)
        self.assertListEqual(songs_collected, [None, "1"])


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

        collected = [o.current_song(), o.next_song()]
        o.interrupt(p2)
        collected.extend(collect(o))

        self.assertListEqual(collected, ["1", "2", "2", "4", "5", "6", "3"])

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

        collected = [o.current_song()]
        o.interrupt(p1)
        collected.extend(collect(o))

        # Two "None"s, one from the initial "current_song", one from the "current_song" in collect()
        expected = list([None, None])
        expected.extend(songs)
        self.assertListEqual(collected, expected)

    def test_no_default_immediately_start(self):
        songs = ["1", "2", "3"]
        p1 = oracles.PlaylistOracle(songs)
        o = oracles.InterruptOracle(None)

        o.interrupt(p1)
        collected = collect(o)

        self.assertListEqual(collected, songs)


class RepeatingOracleTest(unittest.TestCase):

    def test_100_repetitions(self):
        songs = ["1", "2", "3", "4", "5"]
        o = oracles.RepeatingOracle(songs)

        # Collect builds a list of 100, so we'll get "songs" 20 times over.
        collected = collect(o)

        self.assertListEqual(collected, songs * 20)
        self.assertEqual(collected[-1], o.current_song())
        self.assertIsNotNone(o.next_song())

    def test_5_repetitions(self):
        songs = ["1", "2", "3", "4"]
        o = oracles.RepeatingOracle(songs, 3)

        collected = collect(o)

        self.assertListEqual(collected, songs * 3)

    def test_none_as_playlist(self):
        o1 = oracles.RepeatingOracle(None)
        o2 = oracles.RepeatingOracle(None, 52)

        self.assertIsNone(o1.current_song())
        self.assertIsNone(o2.next_song())

    def test_current_song_with_repeating(self):
        songs = ["1", "2", "3"]
        o = oracles.RepeatingOracle(songs, 2)

        collected = [o.current_song(), o.current_song()]
        # "Current song" goes from 1->2, 2->3, 3->1, 1->2.
        for i in range(4):
            o.next_song()
        collected.extend([o.current_song(), o.current_song()])

        # "Current song" goes from 2->3, 3->None, and then repeats.
        for i in range(4):
            o.next_song()
        collected.extend([o.current_song(), o.current_song()])

        self.assertListEqual(collected, ["1", "1", "2", "2", None, None])

    def test_immediate_next_song_returns_second_song(self):
        songs = ["1", "2", "3"]
        o = oracles.RepeatingOracle(songs)

        self.assertEqual(o.next_song(), "2")


if __name__ == '__main__':
    unittest.main()
