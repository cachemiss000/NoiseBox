"""
This module implements a wrapper around the VLC media player object.

This module is UNTESTED because it's nearly impossible to test a contract with a library like vlc.py *well*.
This *should* be handled by e2e or component tests, but it's unclear how to test media playback. Instead,
the goal should be to keep this class as small as simple as possible, with an easy interface we can easily
mock - so that any problems are quickly and immediately apparent with minimal hand-testing, and so that
mock implementations of his class can be used as a stand-in for vlc in classes further up the call stack
when it comes to testing.
"""

import logging
from time import sleep

import vlc  # type: ignore

_VLC_PLAYING_STATES = [
    vlc.State.Playing,
    vlc.State.Buffering,
    vlc.State.Opening,
]

logger = logging.getLogger("media-player")


class UnspecifiedVLCError(Exception):
    """Reserved for errors with VLC we don't really have control over."""
    pass


def next_song_cb(player):
    def cb(*args, **kwargs):
        player.next_song()

    return cb


class Player(object):
    """Wraps the VLC object in order to play media."""

    def __init__(self):
        self.mp = vlc.MediaPlayer()
        self.manager = self.mp.event_manager()
        self.device = None
        self.current_oracle = None

    def play_oracle(self, oracle):
        """Start playing songs as dictated by a given oracle.

        This will start playing oracle.next_song() as soon as the current song is done.
        """
        self.current_oracle = oracle
        self.next_song()

    def play_song(self, song_uri):
        """Play a given song_uri."""
        # TODO: This is a decent stub, but I need to start work on encapsulating the garbage VLC interface.
        media = vlc.Media(song_uri)
        self.mp.set_media(media)
        playing = self.mp.play()
        if playing == -1:
            raise UnspecifiedVLCError("Encountered error while playing uri '%s', check the logs?" % (song_uri,))

    def next_song(self):
        """Start playing the next song from self.current_oracle.

        NOTE: This function DOES NOT work if called from a different thread than the thread used to create
        this object, afaict.
        """
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

    def set_pause(self, value: bool):
        """Pause the current media playback."""
        return self.mp.set_pause(value)

    def toggle_pause(self):
        """Toggle media playback pause. Returns true if now paused, false if playing."""
        self.mp.pause()
        return not self.playing()

    def paused(self):
        return self.mp.get_state() == vlc.State.Paused

    def playing(self):
        return self.mp.get_state() in _VLC_PLAYING_STATES

    def stop(self):
        self.mp.stop()

    def set_device(self, device):
        self.device = device
