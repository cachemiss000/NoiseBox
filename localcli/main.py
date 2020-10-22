"""
The main module for a commandline console controlling the vlc-controller codebase.
"""

import logging
import os
import traceback

from localcli import commands
from localcli.console import Console
from medialogic.controller import Controller
from common.exceptions import UserException
from medialogic.media_library import MediaLibrary
from datetime import datetime
import time
import pathlib

from localcli.print_controller import print_msg

_NOW = datetime.now()
PATH = pathlib.Path(__file__).parent.absolute()
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"),
                    filename="%s/logs/%s-debug.log" % (PATH, _NOW.strftime("%Y-%m-%d %H.%M.%S"),))
logger = logging.getLogger("media-player")


def main_cmd():
    ml = MediaLibrary()
    controller = Controller(ml)
    console = Console()
    q = console.start()

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
        c = class_defn(controller)
        commands_dict[c.name] = c

    # Special commands.
    commands_dict["help"] = commands.Help(commands_dict)
    commands_dict["commands"] = commands.ListCommands(commands_dict)

    for input in q.commands():
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
        if q.terminate:
            break
    console.write("Exiting now...")


if __name__ == '__main__':
    main_cmd()
