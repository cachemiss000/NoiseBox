"""
This module converts proto Oracles into their python equivalent.

We do this to separate the "wire format" from the in-memory format, which allows us to be more flexible in our
implementations, and ensure we're using the best tool for the job in any given situation.

To add a new converter, first write a function that accepts an Oracle protobuf object that's filled in with
your new oracle proto, and then update the function dictionary at the bottom of this file to route inputs
to your function by adding another entry.
"""

import commandserver.media_server_pb2 as ms_pb
from medialogic import oracles

ORACLE_FIELD_NAME = "oracle"


def _convert_null_oracle(_unused) -> oracles.Oracle:
    class NullOracle(oracles.Oracle):
        def current_song(self):
            return None

        def next_song(self):
            return None

    return NullOracle()


def _convert_chain_oracle(oracle: ms_pb.ChainOracle) -> oracles.ChainOracle:
    co = oracles.ChainOracle()
    for oracle in oracle.chain_oracle.oracle_queue:
        co.add(convert(oracle))
    return co


def _convert_switch_oracle(oracle: ms_pb.Oracle) -> oracles.SwitchOracle:
    so = oracles.SwitchOracle()
    so.set_oracle(convert(oracle.switch_oracle.current_oracle))
    return so


def _convert_repeating_oracle(oracle: ms_pb.RepeatingOracle) -> oracles.RepeatingOracle:
    return oracles.RepeatingOracle(oracle.repeating_oracle.media_names, oracle.repeating_oracle.times)


def _convert_playlist_oracle(oracle: ms_pb.Oracle) -> oracles.PlaylistOracle:
    po = oracle.playlist_oracle
    return oracles.PlaylistOracle(po.media_names)


def _convert_interrupt_oracle(oracle: ms_pb.Oracle) -> oracles.InterruptOracle:
    return oracles.InterruptOracle(convert(oracle.interrupt_oracle.default_oracle))


def convert(oracle_proto: ms_pb.Oracle) -> oracles.Oracle:
    if oracle_proto is None:
        return None
    oracle_field_name = oracle_proto.WhichOneof(ORACLE_FIELD_NAME)
    if oracle_field_name is None:
        return None
    return _CONVERSION_FUNCTIONS[oracle_field_name](oracle_proto)


_CONVERSION_FUNCTIONS = {
    ms_pb.Oracle.null_oracle.DESCRIPTOR.name: _convert_null_oracle,
    ms_pb.Oracle.chain_oracle.DESCRIPTOR.name: _convert_chain_oracle,
    ms_pb.Oracle.playlist_oracle.DESCRIPTOR.name: _convert_playlist_oracle,
    ms_pb.Oracle.interrupt_oracle.DESCRIPTOR.name: _convert_interrupt_oracle,
    ms_pb.Oracle.switch_oracle.DESCRIPTOR.name: _convert_switch_oracle,
    ms_pb.Oracle.repeating_oracle.DESCRIPTOR.name: _convert_repeating_oracle,
}
