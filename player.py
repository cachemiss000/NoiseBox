import logging
from time import sleep
from typing import List

import vlc

logger = logging.getLogger("media-player")


class UnspecifiedVLCError(Exception):
    """Reserved for errors with VLC we don't really have control over."""
    pass


def next_song_cb(player):
    def cb(*args, **kwargs):
        player.next_song()

    return cb


class Player(object):
    def __init__(self):
        self.mp = vlc.MediaPlayer()
        self.manager = self.mp.event_manager()
        self.playing = False
        self.device = None
        self.current_oracle = None

    def play_oracle(self, oracle):
        self.current_oracle = oracle
        self.next_song()

    def play_song(self, song_uri):
        # TODO: This is a decent stub, but I need to start work on encapsulating the garbage VLC interface.
        media = vlc.Media(song_uri)
        self.mp.set_media(media)
        playing = self.mp.play()
        if playing == -1:
            raise UnspecifiedVLCError("Encountered error while playing uri '%s', check the logs?" % (song_uri,))

    def next_song(self):
        self.stop()
        if self.current_oracle is None:
            return

        self.mp = vlc.MediaPlayer()
        next_song = self.current_oracle.next_song()
        if next_song is None:
            return
        self.play_song(next_song)
        if self.device:
            # We sleep(1) because otherwise the call won't take if stop() has already been called.
            # (Don't look at me :shrug:)
            sleep(1)
            self.mp.audio_output_device_set(None, self.device)
        self.manager.event_attach(vlc.EventType.MediaPlayerEndReached, next_song_cb(self))

    def pause(self):
        self.mp.set_pause(True)

    def resume(self):
        self.mp.set_pause(False)

    def toggle_pause(self):
        self.mp.pause()

    def stop(self):
        self.mp.stop()

    def set_device(self, device):
        self.device = device
