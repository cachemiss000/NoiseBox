from media_library import MediaLibrary
from player import Player

class Controller(object):
    def __init__(self, media_library : MediaLibrary=None):
        if not media_library:
            media_library = media_library.MediaLibrary()
        self.media_library = media_library
        self.vlc_player = Player()



    def play(self, song_alias: str):
        self.vlc_player.play_song(self.media_library.get_song(song_alias).uri)

    def prepend_to_playlist(self, song_alias):
        pass

    def skip(self):
        pass

    def previous(self):
        pass
