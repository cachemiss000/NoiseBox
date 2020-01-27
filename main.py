from controller import Controller
from media_library import MediaLibrary
from media_library import Song
import time

TEST_SONG = 'X:\Google Drive\Public Fantasticide\Assets\Final Artwork\Music\HNEW.wav'

def main():
    ml = MediaLibrary()
    controller = Controller(ml)
    ml.add_song(Song(alias="test", uri=TEST_SONG))

    controller.play("test")
    time.sleep(15)

if __name__ == '__main__':
    main()