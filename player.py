from time import sleep

import vlc


class UnspecifiedVLCError(Exception):
    """Reserved for errors with VLC we don't really have control over."""
    pass

class Player(object):
    def __init__(self):
        self.mp = vlc.MediaPlayer()
        self.device = None


    def play_song(self, song_uri: str):
        # TODO: This is a decent stub, but I need to start work on encapsulating the garbage VLC interface into something
        # that makes sense externally.
        media = vlc.Media(song_uri)
        self.mp.set_media(media)
        playing = self.mp.play()
        if playing == -1:
            raise UnspecifiedVLCError("Encountered error while playing uri '%s', check the logs?" % (song_uri,))
        if self.device:
            # We sleep(1) because otherwise the call won't take if stop() has already been called.
            # (Don't look at me :shrug:)
            sleep(1)
            self.mp.audio_output_device_set(None, self.device)

    def pause(self):
        self.mp.pause()

    def stop(self):
        self.mp.stop()

    def set_device(self, device):
        self.device = device