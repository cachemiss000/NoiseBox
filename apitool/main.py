import sys

import grpc

import common.commands
from commandserver import media_server_pb2_grpc as ms_pb_grpc

from apitool import commands


def main(*argv):
    channel = grpc.insecure_channel('localhost:50051')
    stub = ms_pb_grpc.MediaControlServiceStub(channel)

    commands_dict = {}
    for c in [
        commands.PlayCommand,
        commands.ListPlaylists
    ]:
        instantiated_command = c(stub)
        commands_dict[instantiated_command.name] = instantiated_command

    # Special commands.
    commands_dict["help"] = common.commands.Help(commands_dict)
    commands_dict["commands"] = common.commands.ListCommands(commands_dict)

    command = argv[1]

    commands_dict[command].process(argv[2:])

if __name__ == '__main__':
    main(*sys.argv)
