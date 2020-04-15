import unittest
from unittest import mock
from unittest.mock import patch

import controller


def create_fake_audio_device(description, next):
    device_mock = mock.MagicMock()
    device_mock.contents.description = description
    device_mock.contents.next = next
    device_mock.freed = False

    def free():
        device_mock.freed = True

    device_mock.free.side_effect = free
    device_mock.__bool__ = lambda x: True
    return device_mock


class FakeNull(object):
    def __init__(self):
        pass

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, FakeNull)


def build_list(*descriptions):
    tail = FakeNull()
    for description in reversed(descriptions):
        bytes_description = bytearray()
        bytes_description.extend(map(ord, description))
        new_item = create_fake_audio_device(description=bytes_description, next=tail)
        tail = new_item
    return tail


def vlc_mock(device_list=None):
    ret_mock = mock.MagicMock()
    ret_mock.mp.audio_output_device_enum.return_value = device_list

    ret_mock.mp.audio_device


class AudioDeviceTest(unittest.TestCase):

    def testBuildAudioDevices(self):
        devices = controller.AudioDevices(build_list("device_1", "device_2"))
        # Yes this is a terrible test, no I'm not fixing it.
        self.assertEqual(repr(devices), '{0: device_1, 1: device_2}')

    @patch('vlc.libvlc_audio_output_device_list_release')
    def testFreeAudioDevice(self, free_device_mock):
        devices = controller.AudioDevices(build_list("device_1"))
        devices.free()
        self.assertEqual(str(devices), controller.FREED_ERROR_STRING)
        assert (free_device_mock.called)

    @patch('vlc.libvlc_audio_output_device_list_release')
    def testFreeAudioDeviceCausesThrow(self, free_device_mock):
        devices = controller.AudioDevices(build_list("device_1"))
        devices.free()
        self.assertRaises(controller.UseAfterFreeException, lambda: devices.device_for_index(1))
        assert (free_device_mock.called)

    def testDeviceForIndex(self):
        devices = controller.AudioDevices(build_list("device_1", "device_2", "device_3"))

        self.assertEqual(str(devices.device_for_index(0)), "device_1")
        self.assertEqual(str(devices.device_for_index(1)), "device_2")
        self.assertEqual(str(devices.device_for_index(2)), "device_3")


if __name__ == '__main__':
    unittest.main()
