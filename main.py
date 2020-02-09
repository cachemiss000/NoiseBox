import argparse
import logging
import os
import sys
from typing import Dict

import commands
from command import Command
from console import Console
from controller import Controller
from media_library import MediaLibrary
from media_library import Song
from datetime import datetime
import time
import pathlib

TEST_SONG = 'X:\Google Drive\Public Fantasticide\Assets\Final Artwork\Music\HNEW.wav'

# TODO(igorham): Adjust this travesty so it goes to a log file like a sane log >.>
_NOW = datetime.now()
PATH = pathlib.Path(__file__).parent.absolute()
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"),
                    filename="%s/%s-debug.log" % (PATH, _NOW.strftime("%Y-%m-%d %H.%M.%S"),))
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

    c = commands.AddSong(controller)

    commands_dict = {
        c.name: c,
    }
    commands_dict["help"] = commands.Help(commands_dict)
    commands_dict["commands"] = commands.ListCommands(commands_dict)

    for input in q.commands():
        if input.command in commands_dict:
            commands_dict[input.command].process(input.arguments)
        else:
            print("Command not found: '%s' - discarding args '%s'" % (input.command, input.arguments))
        if q.terminate:
            break
    console.write("Exiting now...")


if __name__ == '__main__':
    main_cmd()
