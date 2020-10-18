"""
Unittests for commands.py.
"""
import unittest
from typing import List

import commands
from commands import AddSong, IllegalArgument
from controller import Controller
from media_library import MediaLibrary, Song


def get_controller() -> Controller:
    ml = MediaLibrary()
    return Controller(ml)


class AddSongTest(unittest.TestCase):

    def testAddSong(self):
        c = get_controller()
        add = AddSong(c)
        add.do_function("Test", "c:\something.mp3")
        self.assertEqual(c.media_library.get_song("Test"), Song(alias="Test", uri="c:\something.mp3"))

    def testWrongArguments(self):
        c = get_controller()
        add = AddSong(c)

        self.assertRaises(IllegalArgument, lambda: add.do_function(song_alias="", song_path="c:\Something.mp3"))
        self.assertRaises(IllegalArgument, lambda: add.do_function(song_alias="Test", song_path=""))
        self.assertRaises(IllegalArgument, lambda: add.do_function(song_alias="", song_path=""))


class MockPrintController(commands.PrintController):
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
        commands.add_print_controller(mock_printer)

        c.media_library.add_song(Song("TEST", "c:\\something"))
        c.media_library.add_song(Song("TEST2", "c:\\else.mp3"))

        commands.ListSongs(c).do_function()

        self.assertListEqual(mock_printer.get_printed(),
                             ["  TEST: c:\\something",
                              "  TEST2: c:\\else.mp3"])

    def testListEmpty(self):
        c = get_controller()
        mock_printer = MockPrintController()
        commands.add_print_controller(mock_printer)

        commands.ListSongs(c).do_function()
        self.assertListEqual(mock_printer.get_printed(), [])

if __name__ == '__main__':
    unittest.main()
