import argparse
from typing import Dict

import media_library
from command import Command
from controller import Controller


class PrintController(object):
    def print(self, message, *args):
        pass


class SystemPrintController(PrintController):
    def print(self, message, *args):
        print(message, *args)


class MetaPrintController(PrintController):
    def __init__(self):
        self.controllers = []

    def add_print_controller(self, print_controller: PrintController):
        self.controllers.append(print_controller)

    def print(self, message, *args):
        for controller in self.controllers:
            controller.print(message, *args)


PRINT_CONTROLLER = MetaPrintController()
PRINT_CONTROLLER.add_print_controller(SystemPrintController())


def add_print_controller(print_controller: PrintController):
    PRINT_CONTROLLER.add_print_controller(print_controller)


class IllegalArgument(Exception):
    pass


class AddSong(Command):

    def __init__(self, controller: Controller):
        ap = argparse.ArgumentParser(description="Adds a new song to the library")
        ap.add_argument("song_alias", help="Alias by which the song shall forevermore be named")
        ap.add_argument("song_path", help="The URI where this song can be found")
        super().__init__("addsong", ap)
        self.controller = controller

    def do_function(self, song_alias="", song_path=""):
        """Overrides parent "process" function."""
        if song_alias == "":
            raise IllegalArgument("Expected required argument song_alias, but got: \"\"")
        if song_path == "":
            raise IllegalArgument("Expected required argument song_path, but got: \"\"")

        self.controller.media_library.add_song(media_library.Song(alias=song_alias, uri=song_path))


class ListSongs(Command):

    def __init__(self, controller: Controller):
        ap = argparse.ArgumentParser(description="Lists all songs in the library")
        super().__init__("listsongs", ap)
        self.controller = controller

    def do_function(self):
        songs = self.controller.media_library.list_songs()
        for song in songs:
            PRINT_CONTROLLER.print("  %s: %s" % (song.alias, song.uri))


class Help(Command):
    def __init__(self, command_dict: Dict[str, Command]):
        ap = argparse.ArgumentParser("Get help on any command")
        ap.add_argument("command", nargs='?', help="the command on which to receive help")
        super().__init__(name="help", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self, command=""):
        if command == None:
            PRINT_CONTROLLER.print(self.help_string())
            return
        if command not in self.command_dict:
            PRINT_CONTROLLER.print("Cannot find command '%s'.\n\nAvailable commands: '%s'" % (command, self.command_dict.keys()))
            return
        PRINT_CONTROLLER.print(self.command_dict[command].help_string())
        return


class ListCommands(Command):
    def __init__(self, command_dict: Dict[str, Command]):
        ap = argparse.ArgumentParser("List commands")
        super().__init__(name="commands", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self):
        PRINT_CONTROLLER.print("Available commands: [\n  %s\n]" % ("\n  ".join(self.command_dict)))
