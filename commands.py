"""
This uses command.py to implement a series of commandline commands.

These commandline commands perform basic functionality for controlling the media library and the media player, allowing
basic testing from the command line, as well as configuration and scripting for users who know what they're doing.
"""

import argparse
from typing import Dict

import media_library
import json
import pathlib
from command import Command
from controller import Controller
from exceptions import UserException
from print_controller import print_msg


class IllegalArgument(UserException):
    """An exception for illegal commandline arguments"""
    pass


class SafeArgumentParser(argparse.ArgumentParser):
    """This handles errors for argparse, so errors get printed out to the commandline console."""
    def error(self, message):
        print_msg(message)


class ListAudioDevices(Command):
    """List audio devices to the commandline."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="List audio devices")
        super().__init__("listdevices", ap)
        self.controller = controller

    def do_function(self):
        print_msg("Devices: %s" % (self.controller.list_devices()))


class SetDevice(Command):
    """Sets the audio device based on the ListAudioDevices command."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="List audio devices")
        ap.add_argument("device_index", help="The index of the device to set as the output")
        super().__init__("setdevice", ap)
        self.controller = controller

    def do_function(self, device_index=0):
        self.controller.set_device(int(device_index))


class GetDevice(Command):
    """Gets the current audio device and prints it to the command line."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Show the current audio device")
        super().__init__("getdevice", ap)
        self.controller = controller

    def do_function(self):
        print_msg(self.controller.get_device())


class AddSong(Command):
    """Adds a new song to the Media Library."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Adds a new song to the library")
        ap.add_argument("song_alias", help="Alias by which the song shall forevermore be named")
        ap.add_argument("song_path", help="The URI where this song can be found")
        ap.add_argument("--description", type=str, required=False,
                        help="Describe the song to remember what it actually is tho")

        super().__init__("addsong", ap)
        self.controller = controller

    def do_function(self, song_alias="", song_path="", description=""):
        """Overrides parent "process" function."""
        if song_alias == "":
            raise IllegalArgument("Expected required argument song_alias, but got: \"\"")
        if song_path == "":
            raise IllegalArgument("Expected required argument song_path, but got: \"\"")

        self.controller.media_library.add_song(
            media_library.Song(alias=song_alias, uri=song_path, description=description))


class PlaySong(Command):
    """Begins playing a song through the current media device, based on the input song alias."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Play a single song")
        ap.add_argument("song_alias", help="Alias of the song to play")
        super().__init__("playsong", ap)
        self.controller = controller

    def do_function(self, song_alias=""):
        self.controller.play(song_alias)


class Queue(Command):
    """Queues a new song to play after the current set of songs have been played."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Queue up a set of things")
        ap.add_argument("alias", help="Alias of the song or playlist to queue")
        super().__init__("queue", ap)
        self.controller = controller

    def do_function(self, alias=""):
        self.controller.queue(alias)


class Play(Command):
    """Begins playing if not currently playing."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Start playing")
        super().__init__("play", ap)
        self.controller = controller

    def do_function(self):
        if not self.controller.vlc_player.playing:
            self.controller.vlc_player.next_song()


class Pause(Command):
    """Pauses the currently playing song."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Toggle pause the playing song")
        super().__init__("pause", ap)
        self.controller = controller

    def do_function(self):
        self.controller.pause()


class Stop(Command):
    """Stops the currently playing song."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Stop the currently playing song")
        super().__init__("stop", ap)
        self.controller = controller

    def do_function(self):
        self.controller.stop()


class CreatePlaylist(Command):
    """Creates a new playlist in the media library.

    The playlist starts off empty.
    """
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Create a new playlist to start adding songs")
        ap.add_argument("playlist_name", help="The name of the playlist being created.")
        super().__init__("createplaylist", ap)
        self.controller = controller

    def do_function(self, playlist_name=""):
        self.controller.media_library.create_playlist(playlist_name=playlist_name)


class AddSongToPlaylist(Command):
    """Adds a single song to the playlist based on the input alias."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Add a song to a playlist")
        ap.add_argument("playlist_name", help="The name of the playlist to add the song to")
        ap.add_argument("song_alias", help="The alias of the song to add to the playlist")
        super().__init__("add", ap)
        self.controller = controller

    def do_function(self, playlist_name="", song_alias=""):
        self.controller.media_library.add_song_to_playlist(song_alias, playlist_name)


class ListSongs(Command):
    """Lists all songs in the current media library on the commandline."""

    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Lists all songs in the library")
        super().__init__("listsongs", ap)
        self.controller = controller

    def do_function(self):
        songs = self.controller.media_library.list_songs()
        for song in songs:
            if song.description is not None and song.description != "":
                print_msg("  %s: %s || %s" % (song.alias, song.uri, song.description))
            else:
                print_msg("  %s: %s" % (song.alias, song.uri))

class ListPlaylists(Command):
    """Lists all playlists in the current media library on the commandline."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Lists all playlists in the library")
        super().__init__("listplaylists", ap)
        self.controller = controller

    def do_function(self):
        playlists = self.controller.media_library.list_playlists()
        for playlist in playlists:
                print_msg("  %s: %s" % (playlist[0], playlist[1]))


class SaveLibrary(Command):
    """Save the current library to a file in the MediaLibrary sub-folder."""

    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Saves the current media library to disk.")
        ap.add_argument("library_name",
                        help="The name of the library. Used for the file name, with '.json' tacked on to the end.")
        super().__init__("save", ap)
        self.controller = controller

    def do_function(self, library_name=""):
        if library_name == "" or library_name is None:
            raise IllegalArgument("Expected a name for the library. Instead got '%s'" % (library_name,))

        json_str = json.dumps(self.controller.media_library.to_primitive())
        file = open("%s/Media Libraries/%s.json" % (pathlib.Path(__file__).parent.absolute(), library_name,), mode="w")
        file.write(json_str)
        file.close()


class LoadLibrary(Command):
    """Read the library written by SaveLibrary in a previous instance."""

    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Loads a library from disk.")
        ap.add_argument("library_name",
                        help="The name of the library. Used for the file name, with '.json' tacked on to the end.")
        super().__init__("load", ap)
        self.controller = controller

    def do_function(self, library_name=""):
        if library_name == "" or library_name is None:
            raise IllegalArgument("Expected a name for the library. Instead got '%s'" % (library_name,))

        file = open("%s/Media Libraries/%s.json" % (pathlib.Path(__file__).parent.absolute(), library_name), mode="r")
        json_str = file.read()
        ml_primitive = json.loads(json_str)
        self.controller.media_library = media_library.MediaLibrary.from_primitive(ml_primitive)


class DescribeSong(Command):
    """Adds a description to a song in the current media library, based on the alias of the song."""
    def __init__(self, controller: Controller):
        ap = SafeArgumentParser(description="Adds a description to a song.")
        ap.add_argument("song_alias", help="The alias of the song to update.")
        ap.add_argument("description", help="The description to add to the song.")
        super().__init__("describesong", ap)
        self.controller = controller

    def do_function(self, song_alias="", description=""):
        if song_alias == "" or song_alias is None:
            raise IllegalArgument("Expected a name for the song. Instead got '%s'" % (song_alias,))
        if description == "" or description is None:
            raise IllegalArgument("Expected a description for the song. Instead got '%s'" % (description,))
        song = self.controller.media_library.get_song(song_alias)
        song.description = description
        self.controller.media_library.add_song(song, expect_overwrite=True)


class Help(Command):
    """Gets help for a given command."""
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
    """Lists all commands."""
    def __init__(self, command_dict: Dict[str, Command]):
        ap = SafeArgumentParser("List commands")
        super().__init__(name="commands", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self):
        print_msg("Available commands: [\n  %s\n]" % ("\n  ".join(self.command_dict)))
