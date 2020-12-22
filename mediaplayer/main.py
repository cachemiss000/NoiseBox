"""
The main.py module for a commandline console controlling the NoiseBox.
"""
import asyncio
import logging
import os
import pathlib
import time
import traceback
from concurrent import futures
from datetime import datetime

import websockets
from absl import app

import common.commands
from commandserver import command_types_v1 as v1_c_types
from commandserver import v1_server, websocket_muxer
from common.exceptions import UserException
from common.print_controller import print_msg
from localcli import commands
from localcli.console import Console
from medialogic.controller import Controller
from medialogic.media_library import MediaLibrary

_NOW = datetime.now()
PATH = pathlib.Path(__file__).parent.absolute()
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"),
                    filename="%s/../logs/%s-debug.log" % (PATH, _NOW.strftime("%Y-%m-%d %H.%M.%S"),))
logger = logging.getLogger("media-player")
THREAD_POOL = futures.ThreadPoolExecutor(max_workers=10)


class MediaPlayerMaster(object):
    # TODO: It'd be nice to make this thing fully-async... as in, including the "CLI" bits.

    def __init__(self):
        self.ml = MediaLibrary()
        self.controller = Controller(self.ml)
        self.console = Console()
        self.console_output = self.console.start()
        self.media_server = v1_server.MediaServer(self.controller, self.ml)

    def start_local_cli(self):
        # "Normal" commands, which only need the controller.
        commands_dict = {}
        for class_defn in [
            commands.ListAudioDevices,
            commands.GetDevice,
            commands.SetDevice,
            commands.AddSong,
            commands.ListSongs,
            commands.ListPlaylists,
            commands.PlaySong,
            commands.Queue,
            commands.Play,
            commands.Pause,
            commands.Stop,
            commands.CreatePlaylist,
            commands.AddSongToPlaylist,
            commands.SaveLibrary,
            commands.LoadLibrary,
            commands.DescribeSong,
        ]:
            c = class_defn(self.controller)
            commands_dict[c.name] = c

        # Special commands.
        commands_dict["help"] = common.commands.Help(commands_dict)
        commands_dict["commands"] = common.commands.ListCommands(commands_dict)

        for input in self.console_output.commands():
            if input.command in commands_dict:
                try:
                    commands_dict[input.command].process(input.arguments)
                except UserException as e:
                    print(e.user_error_message)
                except Exception as e:
                    traceback.print_exc()
                    time.sleep(1)

            else:
                print_msg("Command not found: '%s' - discarding args '%s'" % (input.command, input.arguments))
            if self.console_output.terminate:
                break
        self.console.write("Exiting now...")

    async def run_server(self):
        v1 = v1_server.MediaServer(self.controller, self.ml)
        muxer = websocket_muxer.WebsocketMuxer()
        muxer.register(v1_c_types.SERVING_ADDRESS, v1)

        await websockets.serve(muxer.handle_session, "localhost", v1_c_types.DEFAULT_PORT)
        print_msg("Server running @ ws://localhost:%s...", v1_c_types.DEFAULT_PORT)


def run(argv):
    mps = MediaPlayerMaster()
    THREAD_POOL.submit(MediaPlayerMaster.start_local_cli, mps)
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(mps.run_server())
    event_loop.run_forever()


if __name__ == '__main__':
    app.run(run)
