import logging
import os
import traceback

import commands
from console import Console
from controller import Controller
from exceptions import UserException
from media_library import MediaLibrary
from media_library import Song
from datetime import datetime
import time
import pathlib

from print_controller import print_msg

TEST_SONG = 'X:\Google Drive\Public Fantasticide\Assets\Music\HNEW.wav'


_NOW = datetime.now()
PATH = pathlib.Path(__file__).parent.absolute()
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"),
                    filename="%s/logs/%s-debug.log" % (PATH, _NOW.strftime("%Y-%m-%d %H.%M.%S"),))
logger = logging.getLogger("media-player")


def main_play():
    ml = MediaLibrary()
    controller = Controller(ml)
    ml.add_song(Song(alias="test", uri=TEST_SONG))

    controller.play("test")
    time.sleep(15)


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
