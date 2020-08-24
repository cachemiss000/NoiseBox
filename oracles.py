from typing import List, Union


class Oracle(object):
    """
    A class which returns the next song to play, assuming the previous song has completed.\
    """

    def next_song(self) -> str:
        """
        Get the next song to play.
        :return: The filename of the song to play, or None if there are no more songs to play.
        """
        pass


class PlaylistOracle(Oracle):
    """
    A semi-immutable Oracle that iterates through a playlist, then returns None.
    """

    def __init__(self, songs: Union[List[str], None]):
        if songs is None:
            songs = []
        self.__playlist = list(songs)
        self.__pointer = 0

    def next_song(self) -> Union[str, None]:
        if self.__pointer >= len(self.__playlist):
            return None
        return_val = self.__playlist[self.__pointer]
        self.__pointer += 1
        return return_val


class ChainOracle(Oracle):
    """
    An Oracle that will iterate through a list of oracles.

    Oracles should be added using the "add" method. This method is append-only, and cannot be undone.
    """

    def __init__(self):
        self.__oracles = []
        self.__pointer = 0

    def next_song(self) -> Union[str, None]:
        song = None
        while song is None:
            # Short circuit the loop if there's nothing left to return.
            if self.__pointer >= len(self.__oracles):
                return None
            if self.__pointer >= len(self.__oracles):
                return None
            oracle = self.__oracles[self.__pointer]
            song = oracle.next_song()
            if song is None:
                self.__pointer += 1
        return song

    def add(self, oracle: Union[Oracle, None]):
        if oracle is None:
            return
        self.__oracles.append(oracle)

    def clear(self):
        self.__oracles.clear()


class SwitchOracle(Oracle):
    """
    Allows switching between multiple oracles
    """

    def __init__(self):
        self.__oracle = None

    def next_song(self) -> Union[str, None]:
        if self.__oracle is None:
            return None
        return self.__oracle.next_song()

    def set_oracle(self, oracle: Union[Oracle, None]):
        self.__oracle = oracle


class InterruptOracle(Oracle):
    """
    Allows interrupting an oracle, then going back to whatever was being done before.
    """

    def __init__(self, default_oracle: Union[Oracle, None]):
        self.__default_oracle = default_oracle
        self.__interrupt_oracle = None

    def next_song(self) -> Union[str, None]:
        if self.__interrupt_oracle is not None:
            next_song = self.__interrupt_oracle.next_song()
            if next_song is not None:
                return next_song

        # If we got here, the interrupt is all out of tunes. Off to the farm with it =(
        self.__interrupt_oracle = None

        if self.__default_oracle is None:
            return None
        return self.__default_oracle.next_song()

    def interrupt(self, oracle: Union[Oracle, None]):
        self.__interrupt_oracle = oracle

    def clear_interrupt(self):
        self.__interrupt_oracle = None


class RepeatingOracle(Oracle):
    """
    Play a playlist, but forever... Will repeat the input list indefinitely.
    """

    def __init__(self, playlist: List[str]):
        self.playlist = playlist
        self.pointer = -1

    def next_song(self) -> str:
        if self.playlist is None:
            return None
        self.pointer += 1
        self.pointer = self.pointer % len(self.playlist)

        return self.playlist[self.pointer]