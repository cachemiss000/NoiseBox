from typing import List

class Song(object):
    """Represents a single song, to be fed into the Media Library."""

    def __init__(self, alias: str, uri: str):
        self.alias = alias
        self.uri = uri

    def __str__(self):
        return "Song{alias: '%s', uri: '%s'}" % (self.alias, self.uri)

class SongAlreadyExistsException(Exception):
    """Thrown when a song with a given alias already exists in the Media Library"""
    pass

class SongNotFoundException(Exception):
    """Thrown when a song with a given alias hasn't been registered with the library yet."""
    pass

class PlaylistNotFoundException(Exception):
    """Thrown when a playlist with a given name isn't found in the media library when adding to it."""
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

    def add_song(self, song: Song, expect_overwrite: bool=False) -> None:
        """Add a song from the song map. Use the stored alias as the alias in the map."""
        if (song.alias in self.song_map and not expect_overwrite):
            raise SongAlreadyExistsException("Song '%s' already exists in the library as '%s'" % (song, self.song_map[song.alias]))
        self.song_map[song.alias] = song

    def get_song(self, song_alias: str) -> Song:
        """Returns a song from the map."""
        if song_alias not in self.song_map:
            raise SongNotFoundException(
                "Could not find song '%s' in map of songs: '%s'" % (song_alias, self.song_map.keys()))
        song = self.song_map[song_alias]
        return Song(alias=song.alias, uri=song.uri)

    def get_playlist(self, playlist_name: str) -> List[str]:
        if  playlist_name not in self.playlists:
            raise PlaylistNotFoundException("Playlist '%s' not found in playlist collection '%s' when adding song '%s'" % (playlist_name, self.playlists.keys(), self.song_map.get(song_alias) if song_alias in self.song_map else song_alias))
        return self.playlists[playlist_name].copy()

    def create_playlist(self, playlist_name: str) -> None:
        self.playlists[playlist_name] = []

    def add_to_playlist(self, song_alias: str, playlist_name: str) -> None:
        self.playlists[playlist_name].append(song_alias)

    def remove_from_playlist(self, song_alias: str, playlist_name: str):
        self.get_playlist(playlist_name).remove(song_alias)