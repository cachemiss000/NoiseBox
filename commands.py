import argparse
from typing import Dict

import media_library
from command import Command
from controller import Controller
from exceptions import UserException
from print_controller import print_msg


class IllegalArgument(UserException):
    pass


class SafeArgumentParser(argparse.ArgumentParser):

    def error(self, message):
        print_msg(message)


class AddSong(Command):

    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Adds a new song to the library")
        ap.add_argument("song_alias", help="Alias by which the song shall forevermore be named")
        ap.add_argument("song_path", help="The URI where this song can be found")
        ap.add_argument("song_description", type=str, required=False, help="Describe the song to remember what it actually is tho")

        super().__init__("addsong", ap)
        self.controller = controller

    def do_function(self, song_alias="", song_path="", song_description=""):
        """Overrides parent "process" function."""
        if song_alias == "":
            raise IllegalArgument("Expected required argument song_alias, but got: \"\"")
        if song_path == "":
            raise IllegalArgument("Expected required argument song_path, but got: \"\"")

        self.controller.media_library.add_song(media_library.Song(alias=song_alias, uri=song_path, description=song_description))


class CreatePlaylist(Command):

    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Create a new playlist to start adding songs")
        ap.add_argument("playlist_name", help="The name of the playlist being created.")
        super().__init__("createplaylist", ap)
        self.controller = controller

    def do_function(self, playlist_name=""):
        self.controller.media_library.create_playlist(playlist_name=playlist_name)


class AddSongToPlaylist(Command):

    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Add a song to a playlist")
        ap.add_argument("playlist_name", help="The name of the playlist to add the song to")
        ap.add_argument("song_alias", help="The alias of the song to add to the playlist")
        super().__init__("addsongtoplaylist", ap)
        self.controller = controller

    def do_function(self, playlist_name="", song_alias=""):
        self.controller.media_library.add_song_to_playlist(song_alias, playlist_name)


class ListSongs(Command):

    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Lists all songs in the library")
        super().__init__("listsongs", ap)
        self.controller = controller

    def do_function(self):
        songs = self.controller.media_library.list_songs()
        for song in songs:
            print_msg("  %s: %s" % (song.alias, song.uri))


class Help(Command):
    def __init__(self, command_dict: Dict[str, Command]):
        ap = SafeArgumentParser("Get help on any command")
        ap.add_argument("command", nargs='?', help="the command on which to receive help")
        super().__init__(name="help", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self, command=""):
        if command is None:
            print_msg(self.help_string())
            return
        if command not in self.command_dict:
            print_msg(
                "Cannot find command '%s'.\n\nAvailable commands: '%s'" % (command, self.command_dict.keys()))
            return
        print_msg(self.command_dict[command].help_string())
        return


class ListCommands(Command):
    def __init__(self, command_dict: Dict[str, Command]):
        ap = SafeArgumentParser("List commands")
        super().__init__(name="commands", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self):
        print_msg("Available commands: [\n  %s\n]" % ("\n  ".join(self.command_dict)))
