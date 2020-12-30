"""Tests controller.py.

Unfortunately, we can't test most of the functionality because they're mostly just 'passthrough's to the VLC module,
and it'd be too complicated to test correctness in a good way.
"""
import unittest
from unittest import mock
from unittest.mock import patch

from absl.testing import absltest

from medialogic import controller


def create_fake_audio_device(description, next_device):
    """Creates a fake audio object that looks like VLC's audio object."""
    device_mock = mock.MagicMock()
    device_mock.contents.description = description
    device_mock.contents.device = description
    device_mock.contents.next = next_device
    device_mock.freed = False

    def free():
        device_mock.freed = True

    device_mock.free.side_effect = free
    device_mock.__bool__ = lambda x: True
    return device_mock


class VLCLinkedListNull(object):
    """Represents a null pointer as you'd see in VLC's linked lists."""

    def __init__(self):
        pass

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, VLCLinkedListNull)


def build_list(*descriptions: str):
    """Builds a list of AudioDevice's as they'd look from VLC using the input list of str descriptions."""
    tail = VLCLinkedListNull()
    for description in reversed(descriptions):
        bytes_description = bytearray()
        bytes_description.extend(map(ord, description))
        new_item = create_fake_audio_device(description=bytes_description, next_device=tail)
        tail = new_item
    return tail


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
        self.assertTrue(free_device_mock.called_count)

    @patch('vlc.libvlc_audio_output_device_list_release')
    def testFreeAudioDeviceCausesThrow(self, free_device_mock):
        devices = controller.AudioDevices(build_list("device_1"))
        devices.free()
        self.assertRaises(controller.UseAfterFreeException, lambda: devices.device_for_index(1))
        self.assertTrue(free_device_mock.called_count)

    def testDeviceForIndex(self):
        devices = controller.AudioDevices(build_list("device_1", "device_2", "device_3"))

        self.assertEqual(str(devices.device_for_index(0)), "device_1")
        self.assertEqual(str(devices.device_for_index(1)), "device_2")
        self.assertEqual(str(devices.device_for_index(2)), "device_3")


if __name__ == '__main__':
    absltest.main()
