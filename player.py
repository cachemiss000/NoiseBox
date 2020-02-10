import vlc


class UnspecifiedVLCError(Exception):
    """Reserved for errors with VLC we don't really have control over."""
    pass

class Player(object):
    def __init__(self):
        self.mp = vlc.MediaPlayer()


    def play_song(self, song_uri: str):
        media = vlc.Media(song_uri)
        self.mp.set_media(media)
        playing = self.mp.play()
        if playing == -1:
            raise UnspecifiedVLCError("Encountered error while playing uri '%s', check the logs?" % (song_uri,))