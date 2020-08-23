from typing import List

import vlc
from vlc import AudioOutputDevice

from media_library import MediaLibrary
from player import Player

FREED_ERROR_STRING = "Invalid object - already freed."
DEFAULT_ENCODING = 'utf-8'

class UseAfterFreeException(Exception):
    pass


class AudioDevice(object):

    def __init__(self, audio_output_device: AudioOutputDevice):
        self.contents = audio_output_device.contents

    def __str__(self):
        return str(self.contents.description, DEFAULT_ENCODING)

    def __repr__(self):
        return str(self)


class AudioDevices(object):

    def __init__(self, audio_device_enum: AudioOutputDevice):
        self.device_list_ptr = audio_device_enum
        device_list = AudioDevices._build_devices(audio_device_enum)
        # The user uses this map to say "I want to play on device 3" instead of "I want to play on device <hex garbage>"
        self.user_device_map = {idx: device for idx, device in enumerate(device_list)}

        # This maps system device names back to real devices. "None" equates to "default"
        self.device_name_map = {None: self.user_device_map.get(0, None)}
        for device in device_list:
            self.device_name_map[str(device.contents.device, DEFAULT_ENCODING)] = device

        self._valid = True

    def valid(self):
        return self._valid

    def free(self):
        if self.valid():
            vlc.libvlc_audio_output_device_list_release(self.device_list_ptr)
            self._valid = False

    def __str__(self):
        if not self.valid():
            return FREED_ERROR_STRING
        output = ("\t%s: %s" % (entry[0], str(entry[1])) for entry in self.user_device_map.items())
        return "\n%s" % ('\n'.join(output),)

    def __repr__(self):
        if not self.valid():
            return "<Invalid object - already freed>"
        return repr(self.user_device_map)

    def device_for_index(self, index: int):
        if not self.valid():
            raise UseAfterFreeException()
        return self.user_device_map[index]

    def device_from_device_name(self, device_name:str):
        return self.device_name_map[device_name]

    @staticmethod
    def _build_devices(audio_output_device: AudioOutputDevice) -> List[AudioDevice]:
        cur = audio_output_device
        output = []
        while cur:
            output.append(AudioDevice(cur))
            cur = cur.contents.next
        return output


class Controller(object):
    def __init__(self, media_library: MediaLibrary = None):
        if not media_library:
            media_library = media_library.MediaLibrary()
        self.media_library = media_library
        self.vlc_player = Player()
        self.devices = AudioDevices(vlc.libvlc_audio_output_device_enum(self.vlc_player.mp))

    def play(self, song_alias: str):
        self.media_library.get(song_alias)
        self.vlc_player.play_song(self.media_library.get_song(song_alias).uri)

    def pause(self):
        self.vlc_player.pause()

    def stop(self):
        self.vlc_player.stop()

    def queue(self, alias: str):
        self.vlc_player.queue(self.media_library.get(alias))

    def list_devices(self) -> List[object]:
        self.devices.free()
        self.devices = AudioDevices(vlc.libvlc_audio_output_device_enum(self.vlc_player.mp))
        return str(self.devices)

    def set_device(self, device_idx):
        self.vlc_player.set_device(self.devices.device_for_index(device_idx).contents.device)

    def get_device(self):
        return str(self.devices.device_from_device_name(self.vlc_player.mp.audio_output_device_get()))

    def skip(self):
        pass

    def previous(self):
        pass
