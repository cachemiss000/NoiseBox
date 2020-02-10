import unittest

import media_library
from media_library import MediaLibrary, Song
from collections import defaultdict
import tempfile

COUNTER_DICT = defaultdict(lambda: 0)

FILE = []


def song(name: str = "", uri: str = ""):
    if name == "":
        test_c = COUNTER_DICT["song_name"]
        name = "test-%04d" % (test_c,)
        COUNTER_DICT["song_name"] += 1
    if uri == "":
        test_c = COUNTER_DICT["song_uri"]
        f = tempfile.TemporaryFile(suffix="_%04d.mp3" % (test_c,))
        COUNTER_DICT["song_uri"] += 1
        FILE.append(f)
        uri = f.name

    return Song(name, uri)


class SongTests(unittest.TestCase):
    def test_add_song(self):
        ml = MediaLibrary()
        s = song()
        ml.add_song(s)
        self.assertDictEqual(ml.song_map, {s.alias: s})

    def test_accidental_overwrite_throws(self):
        ml = MediaLibrary()
        s = song(name="test")

        ml.add_song(s)
        self.assertRaises(media_library.AlreadyExistsException,
                          lambda: ml.add_song(song(name="test"), expect_overwrite=False))

    def test_checks_uri(self):
        ml = MediaLibrary()

        self.assertRaises(media_library.NotFoundException,
                          lambda: ml.add_song(song(uri="C:\something\ invalid.mp3")))

    def test_overwrite_works_when_expected(self):
        ml = MediaLibrary()
        s1 = song(name="test")
        s2 = song(name="test")
        ml.add_song(s1)
        ml.add_song(s2, expect_overwrite=True)
        self.assertDictEqual(ml.song_map, {"test": s2})

    def test_adding_multiple_songs(self):
        ml = MediaLibrary()
        s1 = song()
        s2 = song()

        ml.add_song(s1)
        ml.add_song(s2)

        self.assertDictEqual(ml.song_map, {s1.alias: s1, s2.alias: s2})

    def test_list_songs_without_songs_works(self):
        ml = MediaLibrary()
        self.assertListEqual(ml.list_songs(), [])

    def test_list_songs_with_songs_works(self):
        ml = MediaLibrary()
        s1 = song()
        s2 = song()
        s3 = song()
        ml.add_song(s1)
        ml.add_song(s2)
        ml.add_song(s3)

        self.assertListEqual(ml.list_songs(), [s1, s2, s3])

    def test_adding_non_song_throws(self):
        ml = MediaLibrary()
        self.assertRaisesRegex(media_library.IllegalArgument, ".*'alias'.*'str'", lambda: ml.add_song("alias"))


class PlaylistTests(unittest.TestCase):

    def test_create_playlist(self):
        ml = MediaLibrary()
        ml.create_playlist("something")

        self.assertDictEqual(ml.playlists, {"something": []})

    def test_add_song(self):
        ml = MediaLibrary()
        s = song()

        ml.create_playlist("something")
        ml.add_song(s)
        ml.add_song_to_playlist(song_alias=s.alias, playlist_name="something")

        self.assertDictEqual(ml.playlists, {"something": [s.alias]})

    def test_add_multiple_songs(self):
        ml = MediaLibrary()
        s1 = song()
        s2 = song()

        ml.create_playlist("test")
        ml.add_song(s1)
        ml.add_song(s2)
        ml.add_song_to_playlist(song_alias=s1.alias, playlist_name="test")
        ml.add_song_to_playlist(song_alias=s2.alias, playlist_name="test")

        self.assertDictEqual(ml.playlists, {"test": [s1.alias, s2.alias]})

    def test_multiple_playlists(self):
        ml = MediaLibrary()
        s1 = song()
        s2 = song()

        ml.add_song(s1)
        ml.add_song(s2)
        ml.create_playlist("test-1")
        ml.create_playlist("test-2")

        ml.add_song_to_playlist(s1.alias, "test-1")
        ml.add_song_to_playlist(s2.alias, "test-2")

        self.assertDictEqual(ml.playlists, {"test-1": [s1.alias], "test-2": [s2.alias]})

    def test_get_playlist(self):
        ml = MediaLibrary()
        s = song()
        ml.create_playlist("test")
        ml.add_song(s)
        ml.add_song_to_playlist(s.alias, "test")
        self.assertListEqual(ml.get_playlist("test"), [s.alias])

    def test_get_playlist_write_protected(self):
        """Make sure users can't change playlists by getting them."""
        ml = MediaLibrary()
        s1 = song()
        s2 = song()
        ml.create_playlist("test")
        ml.add_song(s1)
        ml.add_song(s2)

        ml.add_song_to_playlist(s1.alias, "test")
        ml.get_playlist("test").append(s2)

        self.assertListEqual(ml.get_playlist("test"), [s1.alias])

    def test_cant_add_song_directly(self):
        """Make sure users can't change playlists by getting them."""
        ml = MediaLibrary()
        s = song()
        ml.create_playlist("test")
        ml.add_song(s)

        self.assertRaisesRegex(media_library.IllegalArgument, ".*Song{.*Song", lambda: ml.add_song_to_playlist(s, "test"))

    def test_overwrite_erases_playlist(self):
        ml = MediaLibrary()
        s = song()
        ml.add_song(s)
        ml.create_playlist("test")
        ml.add_song_to_playlist(s.alias, "test")
        ml.create_playlist("test", expect_overwrite=True)

        self.assertListEqual(ml.get_playlist("test"), [])

if __name__ == '__main__':
    unittest.main()
