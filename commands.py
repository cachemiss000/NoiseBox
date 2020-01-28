import argparse
from typing import Dict

import media_library
from command import Command
from controller import Controller


class AddSong(Command):

    def __init__(self, controller: Controller):
        ap = argparse.ArgumentParser(description="Adds a new song to the library")
        ap.add_argument("song_alias", help="Alias by which the song shall forevermore be named")
        ap.add_argument("song_path", help="The URI where this song can be found")
        super().__init__("addsong", ap)
        self.controller = controller

    def do_function(self, song_alias="", song_path=""):
        """Overrides parent "process" function."""
        self.controller.media_library.add_song(media_library.Song(alias=song_alias, uri=song_path))


class Help(Command):
    def __init__(self, command_dict: Dict[str, Command]):
        ap = argparse.ArgumentParser("Get help on any command")
        ap.add_argument("command", nargs='?', help="the command on which to receive help")
        super().__init__(name="help", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self, command=""):
        if command == None:
            print(self.help_string())
            return
        if command not in self.command_dict:
            print("Cannot find command '%s'.\n\nAvailable commands: '%s'" % (command, self.command_dict.keys()))
            return
        print(self.command_dict[command].help_string())
        return


class ListCommands(Command):
    def __init__(self, command_dict: Dict[str, Command]):
        ap = argparse.ArgumentParser("List commands")
        super().__init__(name="commands", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self):
        print("Available commands: [\n  %s\n]" % ("\n  ".join(self.command_dict)))
