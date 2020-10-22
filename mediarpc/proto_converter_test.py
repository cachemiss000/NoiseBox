"""
Tests for proto_converter.py, ensuring that the "convert()" function accurately turns pb oracles
from media_server.proto into oracles from oracles.py.
"""
import itertools
import unittest
from common import test_utils as utils
from medialogic import oracles
import mediarpc.media_server_pb2 as ms_pb
import mediarpc.proto_converter as converter


def wrap_base_oracle(oracle):
    o = ms_pb.Oracle(id=1)
    if isinstance(oracle, ms_pb.NullOracle):
        o.null_oracle.CopyFrom(oracle)
        return o
    if isinstance(oracle, ms_pb.PlaylistOracle):
        o.playlist_oracle.CopyFrom(oracle)
        return o
    if isinstance(oracle, ms_pb.InterruptOracle):
        o.interrupt_oracle.CopyFrom(oracle)
        return o
    if isinstance(oracle, ms_pb.ChainOracle):
        o.chain_oracle.CopyFrom(oracle)
        return o
    if isinstance(oracle, ms_pb.SwitchOracle):
        o.switch_oracle.CopyFrom(oracle)
        return o
    if isinstance(oracle, ms_pb.RepeatingOracle):
        o.repeating_oracle.CopyFrom(oracle)
        return o
    raise NotImplementedError("Have not yet implemented conversion for '%s'" % (oracle.DESCRIPTOR.name))


class NullOracleTest(unittest.TestCase):
    def test_null_conversion(self):
        no = ms_pb.NullOracle()
        converted = converter.convert(wrap_base_oracle(no))

        self.assertIsNotNone(converted)
        self.assertIsNone(converted.next_song())
        self.assertIsNone(converted.current_song())


class PlaylistOracleTest(unittest.TestCase):
    def test_playlist_conversion(self):
        po = ms_pb.PlaylistOracle()
        playlist = ["one", "two", "three"]
        po.media_names.extend(playlist)
        converted = converter.convert(wrap_base_oracle(po))

        collected_songs = utils.collect(converted)

        self.assertListEqual(collected_songs, playlist)

    def test_empty_playlist(self):
        po = ms_pb.PlaylistOracle()
        converted = converter.convert(wrap_base_oracle(po))
        collected_songs = utils.collect(converted)

        self.assertListEqual(collected_songs, [None])


class InterruptOracleTest(unittest.TestCase):
    def test_oracle_conversion(self):
        # Arrange
        po1 = ms_pb.PlaylistOracle()
        playlist1 = ["one", "two", "three"]
        po1.media_names.extend(playlist1)

        io = ms_pb.InterruptOracle()
        io.default_oracle.CopyFrom(wrap_base_oracle(po1))

        playlist2 = ["four", "five"]
        po2 = oracles.PlaylistOracle(playlist2)

        converted = converter.convert(wrap_base_oracle(io))

        # Act
        collected = [converted.current_song()]
        converted.interrupt(po2)
        # Drop the first entry, which was already collected
        collected.extend(utils.collect(converted)[1:])

        # Assert
        self.assertListEqual(collected, ["one", "four", "five", "two", "three"])


class ChainOracleTest(unittest.TestCase):
    def test_chaining_oracles(self):
        # Arrange
        po1 = ms_pb.PlaylistOracle()
        playlist1 = ["one", "two", "three"]
        po1.media_names.extend(playlist1)

        po2 = ms_pb.PlaylistOracle()
        playlist2 = ["four", "five", "six"]
        po2.media_names.extend(playlist2)

        co = ms_pb.ChainOracle()
        co.oracle_queue.append(wrap_base_oracle(po1))
        co.oracle_queue.append(wrap_base_oracle(po2))

        # Act
        converted = converter.convert(wrap_base_oracle(co))

        # Assert
        collected = utils.collect(converted)
        self.assertListEqual(collected, list(itertools.chain(playlist1, playlist2)))

    def test_no_oracles(self):
        co = ms_pb.ChainOracle()
        converted = converter.convert(wrap_base_oracle(co))

        collected = utils.collect(converted)

        self.assertListEqual(collected, [None])

    def test_chain_empty_oracle(self):
        # Arrange
        po1 = ms_pb.PlaylistOracle()
        playlist1 = ["one", "two", "three"]
        po1.media_names.extend(playlist1)

        po2 = ms_pb.PlaylistOracle()
        playlist2 = ["four", "five", "six"]
        po2.media_names.extend(playlist2)

        co = ms_pb.ChainOracle()
        co.oracle_queue.append(wrap_base_oracle(po1))
        co.oracle_queue.append(wrap_base_oracle(ms_pb.NullOracle()))
        co.oracle_queue.append(wrap_base_oracle(po2))

        # Act
        converted = converter.convert(wrap_base_oracle(co))

        # Assert
        collected = utils.collect(converted)
        self.assertListEqual(collected, list(itertools.chain(playlist1, playlist2)))

    def test_empty_first_oracle(self):
        # Arrange
        po1 = ms_pb.PlaylistOracle()
        playlist1 = ["one", "two", "three"]
        po1.media_names.extend(playlist1)

        po2 = ms_pb.PlaylistOracle()
        playlist2 = ["four", "five", "six"]
        po2.media_names.extend(playlist2)

        co = ms_pb.ChainOracle()
        co.oracle_queue.append(wrap_base_oracle(ms_pb.NullOracle()))
        co.oracle_queue.append(wrap_base_oracle(po1))
        co.oracle_queue.append(wrap_base_oracle(po2))

        # Act
        converted = converter.convert(wrap_base_oracle(co))

        # Assert
        collected = utils.collect(converted)
        self.assertListEqual(collected, list(itertools.chain(playlist1, playlist2)))

    def test_empty_last_oracle(self):
        # Arrange
        po1 = ms_pb.PlaylistOracle()
        playlist1 = ["one", "two", "three"]
        po1.media_names.extend(playlist1)

        po2 = ms_pb.PlaylistOracle()
        playlist2 = ["four", "five", "six"]
        po2.media_names.extend(playlist2)

        co = ms_pb.ChainOracle()
        co.oracle_queue.append(wrap_base_oracle(po1))
        co.oracle_queue.append(wrap_base_oracle(po2))
        co.oracle_queue.append(wrap_base_oracle(ms_pb.NullOracle()))

        # Act
        converted = converter.convert(wrap_base_oracle(co))

        # Assert
        collected = utils.collect(converted)
        self.assertListEqual(collected, list(itertools.chain(playlist1, playlist2)))


class SwitchOracleTest(unittest.TestCase):

    def test_no_oracle(self):
        so = ms_pb.SwitchOracle()

        songs = ["one", "two"]
        po = oracles.PlaylistOracle(songs)

        converted = converter.convert(wrap_base_oracle(so))

        collected1 = utils.collect(converted)
        converted.set_oracle(po)
        collected2 = utils.collect(converted)

        self.assertListEqual(collected1, [None])
        self.assertListEqual(collected2, [None, "one", "two"])

    def test_oracle_set(self):
        so = ms_pb.SwitchOracle()
        songs = ["one", "two"]
        po = ms_pb.PlaylistOracle()
        po.media_names.extend(songs)
        so.current_oracle.CopyFrom(wrap_base_oracle(po))

        converted = converter.convert(wrap_base_oracle(so))
        collected = utils.collect(converted)

        self.assertListEqual(collected, songs)


class RepeatingOracleTest(unittest.TestCase):
    def test_no_oracle(self):
        ro = ms_pb.RepeatingOracle()

        converted = converter.convert(wrap_base_oracle(ro))
        collected = utils.collect(converted)

        self.assertListEqual(collected, [None])

    def test_no_repeats(self):
        ro = ms_pb.RepeatingOracle()
        songs = ["one", "two", "three"]

        ro.times = 0
        ro.media_names.extend(songs)

        converted = converter.convert(wrap_base_oracle(ro))
        collected = utils.collect(converted)

        self.assertListEqual(collected, [None])

    def test_one_repeat(self):
        ro = ms_pb.RepeatingOracle()
        songs = ["one", "two", "three"]

        ro.times = 1
        ro.media_names.extend(songs)

        converted = converter.convert(wrap_base_oracle(ro))
        collected = utils.collect(converted)

        self.assertListEqual(collected, ["one", "two", "three"])

    def test_three_repeats(self):
        ro = ms_pb.RepeatingOracle()
        songs = ["one", "two", "three"]

        ro.times = 3
        ro.media_names.extend(songs)

        converted = converter.convert(wrap_base_oracle(ro))
        collected = utils.collect(converted)

        self.assertListEqual(collected, ["one", "two", "three"] * 3)

    def test_repeat_nothing(self):
        ro = ms_pb.RepeatingOracle()
        songs = []

        ro.times = 50

        converted = converter.convert(wrap_base_oracle(ro))
        collected = utils.collect(converted)

        self.assertListEqual(collected, [None])


if __name__ == '__main__':
    unittest.main()
