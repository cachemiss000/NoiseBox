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
import time

TEST_SONG = 'X:\Google Drive\Public Fantasticide\Assets\Final Artwork\Music\HNEW.wav'

# TODO(igorham): Adjust this travesty so it goes to a log file like a sane log >.>
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logger = logging.getLogger(__name__)
h = logging.StreamHandler(sys.stderr)
h.flush = sys.stderr.flush
logger.addHandler(h)


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
        # Kinda a bad idea, but like...
        # Remove if this causes problems.
        # And really remove once we move logging to a file WHERE IT BELONGS.
        logger.handlers[0].flush()
    console.write("Exiting now...")


if __name__ == '__main__':
    main_cmd()
