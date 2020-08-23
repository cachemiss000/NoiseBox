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
        logger.info("Got next song callback")
        player.next_song()
    return cb

class Player(object):
    def __init__(self):
        self.song_list = []
        self.mp = vlc.MediaPlayer()
        self.manager = self.mp.event_manager()
        self.playing = False
        self.device = None

    def play_song(self, song_uri: str):
        # TODO: This is a decent stub, but I need to start work on encapsulating the garbage VLC interface into something
        # that makes sense externally.
        media = vlc.Media(song_uri)
        self.mp.set_media(media)
        playing = self.mp.play()
        if len(self.song_list) > 0:
            self.manager.event_attach(vlc.EventType.MediaPlayerEndReached, next_song_cb(self))
        if playing == -1:
            raise UnspecifiedVLCError("Encountered error while playing uri '%s', check the logs?" % (song_uri,))
        if self.device:
            # We sleep(1) because otherwise the call won't take if stop() has already been called.
            # (Don't look at me :shrug:)
            sleep(1)
            self.mp.audio_output_device_set(None, self.device)

    def play(self):
        if not self.playing:
            self.next_song()

    def next_song(self):
        next_song = self.song_list[0]
        del self.song_list[0]

        logger.info("Playing next song '%s', with queue of '%s'." % (next_song, self.song_list))

        self.play_song(next_song)


    def queue(self, song_uri):
        if isinstance(song_uri, list):
            self.song_list.extend(song_uri)
            return
        self.song_list.append(song_uri)

    def pause(self):
        self.mp.pause()

    def stop(self):
        self.mp.stop()

    def set_device(self, device):
        self.device = device