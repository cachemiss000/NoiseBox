from console import Console
from controller import Controller
from media_library import MediaLibrary
from media_library import Song
import time

TEST_SONG = 'X:\Google Drive\Public Fantasticide\Assets\Final Artwork\Music\HNEW.wav'


def main_play():
    ml = MediaLibrary()
    controller = Controller(ml)
    ml.add_song(Song(alias="test", uri=TEST_SONG))

    controller.play("test")
    time.sleep(15)


def main_cmd():
    console = Console()
    q = console.start()

    for v in q.commands():
        print("Received %s" % (v,))
        if q.terminate:
            break
    console.write("Exiting now...")


if __name__ == '__main__':
    main_cmd()
