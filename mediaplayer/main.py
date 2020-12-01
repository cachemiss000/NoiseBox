"""
The main.py module for a commandline console controlling the vlc-controller codebase.
"""

import logging
import os
import traceback
from concurrent import futures

import grpc

import common.commands
from localcli import commands
from localcli.console import Console
from medialogic.controller import Controller
from common.exceptions import UserException
from medialogic.media_library import MediaLibrary
from commandserver import server
from commandserver import media_server_pb2_grpc as ms_pb_grpc
from datetime import datetime
import time
import pathlib

from localcli.print_controller import print_msg

_NOW = datetime.now()
PATH = pathlib.Path(__file__).parent.absolute()
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"),
                    filename="%s/../logs/%s-debug.log" % (PATH, _NOW.strftime("%Y-%m-%d %H.%M.%S"),))
logger = logging.getLogger("media-player")
THREAD_POOL = futures.ThreadPoolExecutor(max_workers=10)

class MediaPlayerMaster(object):
    def __init__(self):
        self.ml = MediaLibrary()
        self.controller = Controller(self.ml)
        self.console = Console()
        self.console_output = self.console.start()
        self.media_server = server.MediaServer(self.controller, self.ml)

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

    def start_server(self):
        grpc_server = grpc.server(THREAD_POOL)
        ms_pb_grpc.add_MediaControlServiceServicer_to_server(self.media_server, grpc_server)
        # Copied from protobuf 2 documentation, because that's how you pick ports, right?
        grpc_server.add_insecure_port('[::]:50051')
        grpc_server.start()
        grpc_server.wait_for_termination()


if __name__ == '__main__':
    mps = MediaPlayerMaster()
    THREAD_POOL.submit(MediaPlayerMaster.start_local_cli, mps)
    mps.start_server()
