from typing import List
import os

from exceptions import UserException


def _check_file_exists(song_uri):
    if os.path.isfile(song_uri):
        return
    raise NotFoundException("Could not find file '%s'" % (song_uri,))


class Song(object):
    """Represents a single song, to be fed into the Media Library."""

    def __init__(self, alias: str, uri: str, description: str = ""):
        self.alias = alias
        _check_file_exists(uri)
        self.uri = uri
        self.description = description

    def __str__(self):
        return "Song{alias: '%s', uri: '%s', description: '%s'}" % (self.alias, self.uri, self.description)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        """We explicitly ignore the "description" field because it's not a 'key'."""
        if not isinstance(other, Song):
            return False
        if self.alias == other.alias and self.uri == other.uri:
            return True


class NotFoundException(UserException):
    """Thrown when a song with a given alias hasn't been registered with the library yet."""
    pass


class AlreadyExistsException(UserException):
    """Thrown when a playlist with a given name already exists."""
    pass


class IllegalArgument(UserException):
    """Thrown when an input argument is invalid."""
    pass


class MediaLibrary(object):
    """
    Holds music for future reference.

    This makes it easier to reference songs & playlists using short, human-readable phrases instead of goddamn URIs...

    Makes defensive copies on every "get" function.
     """

    def __init__(self):
        self.song_map = {}
        self.playlists = {}

    def add_song(self, song: Song, expect_overwrite: bool = False) -> None:
        """Add a song from the song map. Use the stored alias as the alias in the map."""
        if not isinstance(song, Song):
            raise IllegalArgument("Expected object '%s' to be a Song object, instead got a '%s'" %
                                  (song, type(song).__name__))
        if song.alias in self.song_map and not expect_overwrite:
            raise AlreadyExistsException(
                "Song '%s' already exists in the library as '%s'" % (song, self.song_map[song.alias]))
        self.song_map[song.alias] = song

    def get_song(self, song_alias: str) -> Song:
        """Returns a song from the map."""
        if song_alias not in self.song_map:
            raise NotFoundException(
                "Could not find song '%s' in map of songs: '%s'" % (song_alias, self.song_map.keys()))
        song = self.song_map[song_alias]
        return Song(alias=song.alias, uri=song.uri)

    def list_songs(self) -> List[Song]:
        return list(self.song_map.values())

    def get_playlist(self, playlist_name: str) -> List[str]:
        if playlist_name not in self.playlists:
            raise NotFoundException("Playlist '%s' not found in playlist collection '%s'" % (
                playlist_name, self.playlists.keys()))
        return list(self.playlists[playlist_name])

    def create_playlist(self, playlist_name: str, expect_overwrite: bool = False) -> None:
        if playlist_name == "":
            raise IllegalArgument("Expected name for playlist, got \"\"")
        existing_playlist = self.playlists.get(playlist_name, None)
        if existing_playlist is not None and not expect_overwrite:
            raise AlreadyExistsException(
                "Playlist '%s' already exists! {%s}" % (playlist_name, existing_playlist))
        self.playlists[playlist_name] = []

    def add_song_to_playlist(self, song_alias: str, playlist_name: str) -> None:
        if playlist_name not in self.playlists:
            raise NotFoundException("Couldn't find playlist '%s' when adding song '%s'" % (playlist_name, song_alias))
        if not isinstance(song_alias, str):
            raise IllegalArgument(
                "Expected object '%s' of type '%s' to be a string song alias" % (
                    song_alias, type(song_alias).__name__), )

        self.playlists[playlist_name].append(song_alias)

    def remove_from_playlist(self, song_alias: str, playlist_name: str):
        self.get_playlist(playlist_name).remove(song_alias)
