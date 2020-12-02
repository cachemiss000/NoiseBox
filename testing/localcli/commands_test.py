"""
Unittests for commands.py.
"""
import unittest
from typing import List
from unittest import mock

from localcli import commands
from localcli.commands import AddSong, IllegalArgument
from common import print_controller
from medialogic.controller import Controller
from medialogic.media_library import MediaLibrary, Song


def get_controller() -> Controller:
    ml = MediaLibrary()
    return Controller(ml)


class AddSongTest(unittest.TestCase):

    def testAddSong(self):
        c = get_controller()
        add = AddSong(c)
        with mock.patch("medialogic.media_library.os.path.isfile", lambda _: True):
            add.do_function("Test", "c:\something.mp3")
            self.assertEqual(c.media_library.get_song("Test"), Song(alias="Test", uri="c:\something.mp3"))

    def testWrongArguments(self):
        c = get_controller()
        add = AddSong(c)

        self.assertRaises(IllegalArgument, lambda: add.do_function(song_alias="", song_path="c:\Something.mp3"))
        self.assertRaises(IllegalArgument, lambda: add.do_function(song_alias="Test", song_path=""))
        self.assertRaises(IllegalArgument, lambda: add.do_function(song_alias="", song_path=""))


class MockPrintController(print_controller.PrintController):
    def __init__(self):
        self.printed = []

    def print(self, message, *args):
        self.printed.append(message % args)

    def get_printed(self) -> List[str]:
        return self.printed


class ListSongsTest(unittest.TestCase):

    def testListSongs(self):
        c = get_controller()
        mock_printer = MockPrintController()
        print_controller.add_print_controller(mock_printer)

        with mock.patch("medialogic.media_library.os.path.isfile", lambda _: True):
            c.media_library.add_song(Song("TEST", "c:\\something"))
            c.media_library.add_song(Song("TEST2", "c:\\else.mp3"))

        commands.ListSongs(c).do_function()

        self.assertListEqual(mock_printer.get_printed(),
                             ["  TEST: c:\\something",
                              "  TEST2: c:\\else.mp3"])

    def testListEmpty(self):
        c = get_controller()
        mock_printer = MockPrintController()
        print_controller.add_print_controller(mock_printer)

        commands.ListSongs(c).do_function()
        self.assertListEqual(mock_printer.get_printed(), [])


if __name__ == '__main__':
    unittest.main()
