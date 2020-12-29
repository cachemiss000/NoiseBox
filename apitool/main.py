import asyncio
import sys

import websockets

import common.commands
from apitool import commands
from commandserver.server_types import v1_command_types


def run(*argv):
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(async_inner(*argv))


async def async_inner(*argv):
    client: websockets.WebSocketClientProtocol = await websockets.connect(
        "ws://localhost:%s%s" % (v1_command_types.DEFAULT_PORT, v1_command_types.SERVING_ADDRESS))

    commands_dict = {}
    for c in [
        commands.PlayCommand,
        commands.ListPlaylists
    ]:
        instantiated_command = c(client)
        commands_dict[instantiated_command.name] = instantiated_command

    # Special commands.
    commands_dict["help"] = common.commands.Help(commands_dict)
    commands_dict["commands"] = common.commands.ListCommands(commands_dict)

    command = argv[0]

    await commands_dict[command].process(list(argv[1:]))

    await client.close()


if __name__ == '__main__':
    run(*sys.argv)
