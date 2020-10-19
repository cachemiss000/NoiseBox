"""
This module defines idioms and classes used to manipulate playlists during playback programmatically.

"Oracles" are objects that understand what song is playing, and what song to play next. Through defining
a variety of implementations, you can setup a system to ensure the desired playback of songs over time. This
module both defines the 'oracle' class, as well as many of those implementations.

Because these objects are inherently mutable, the interfaces require a number of guarantees and contracts, and
also come with a slew of edge cases. Be careful when manipulating any code that looks 'fishy' or 'complicated'
in this file - while the tests cover a lot of the weird edge cases, it's impossible to guarantee they cover
everything.
"""
from typing import List, Union


class Oracle(object):
    """
    A class which returns the next song to play, assuming the previous song has completed.

    NOTE: When created, the "first song" is returned by "current_song()", while the *SECOND* song is returned
    when you call "next_song()". As a result, you will miss things if you just start by calling "next_song()", although
    after you collect "current_song()" the first time, you'll get the full playlist if you continue calling "next_song()
    until you get "None".

    "current_song" will always return the same value after it is called once, until you call "next_song" (on
    properly-implemented clients)
    """

    def next_song(self) -> Union[str, None]:
        """
        Get the next song to play.
        :return: The filename of the song to play, or None if there are no more songs to play.
        """
        pass

    def current_song(self) -> Union[str, None]:
        """
        Get the current song playing.

        This is ALWAYS the last song returned by "next_song", and will never change after calling it *until* you
        call "next_song" again, .

        This is useful for situations where you stopped and want to restart, or otherwise don't want to advance
        the currently-playing song, but do need the filepath again.

        This WILL NEVER change internal state except for memoization, which can lead to some *seriously* funky
        consequences. For instance, if you have a chain oracle with [PlaylistOracle[None], PlaylistOracle[1, 2, 3]] and
         call "current_song", it'll return None while "next_song" will return "1". If you create a switch oracle and
         then switch it after calling "next_song", it'll still return the original song. And so on. Tons of edge cases
         when messing with state =(

        :return:The filename of the current song that should be playing.
        """
        pass


class MemoizingOracle(Oracle):
    """
    An oracle which fulfills the memoizing aspects of the interface as laid out above.

    We separate the implementation of this oracle because memoizing is complicated and a pain, especially when you
    need to do it 15 times. We don't put this logic into the base Oracle class, however, because the PlaylistOracle
    and other simple oracles don't need it.
    """

    def __init__(self):
        self.has_memoized_current_song = False
        self.memoized_current_song = None

    def _inner_next_song(self) -> Union[str, None]:
        raise NotImplementedError("No implementation found for __inner_next_song in '%s'" % (self.__class__,))

    def _inner_get_first_song(self) -> Union[str, None]:
        raise NotImplementedError("No implementation found for __inner_next_song in '%s'" % (self.__class__,))

    def current_song(self):
        # We make the distinction between "has_memoized_current_song" and "memoized_current_song != None"
        # because __inner_current_song *might* return None.
        if not self.has_memoized_current_song:
            self.memoized_current_song = self._inner_get_first_song()
            self.has_memoized_current_song = True
        return self.memoized_current_song

    def next_song(self):
        next_song = self._inner_next_song()
        self.memoized_current_song = next_song
        self.has_memoized_current_song = True
        return next_song


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
        self.__pointer += 1
        if self.__pointer >= len(self.__playlist):
            return None
        return_val = self.__playlist[self.__pointer]
        return return_val

    def current_song(self) -> Union[str, None]:
        if self.__pointer >= len(self.__playlist):
            return None
        return self.__playlist[self.__pointer]


class ChainOracle(MemoizingOracle):
    """
    An Oracle that will iterate through a list of oracles.

    Oracles should be added using the "add" method. This method is append-only, and cannot be undone.
    """

    def __init__(self):
        super(ChainOracle, self).__init__()
        self.__oracles = []
        # Start at -1 so we know to grab the first song from the first oracle using "current_song" instead of
        # assuming we've already started on that oracle and jumping straigt to "next_song"
        self.__pointer = 0

        # We want "next_song" to return the second song if it's called before ever calling "current_song()" for
        # reasons that are stupid and hard to explain at 1am. Play with the tests if you don't believe me.
        #
        # Otherwise, this variable basically means "If true, take the "current_song()" of the current oracle instead
        # of the "next_song()" because we haven't returned the "current_song()" yet.
        self.__has_drawn_from_oracle = True

    def _inner_next_song(self) -> Union[str, None]:
        song = None
        while song is None:
            current_oracle = self.__get_current_oracle()
            if current_oracle is None:
                return None

            # This covers some nasty edge cases, like "going off the edge in one call
            # to "next_song()" and then adding an oracle and calling "next_song()" again.
            if self.__has_drawn_from_oracle:
                song = current_oracle.next_song()
            else:
                song = current_oracle.current_song()

            # This is so ugly I hate it. Please someone help.
            if song is None:
                self.__pointer += 1
                self.__has_drawn_from_oracle = False

        self.__has_drawn_from_oracle = True
        return song

    def __get_current_oracle(self) -> Union[Oracle, None]:
        """A quick encapsulation of the 'get next' logic to make code function more smoothly

        :return the current oracle, and empty oracle if we haven't called "NextSong" yet, and
        """
        if self.__pointer >= len(self.__oracles):
            return None

        return self.__oracles[self.__pointer]

    def _inner_get_first_song(self) -> Union[str, None]:
        if self.__oracles is None or len(self.__oracles) == 0:
            # Ensure that next time next_song() gets called, we force ourselves to play the first song of whatever
            # oracles have been added since then.
            self.__oracles.insert(0, PlaylistOracle([]))
            return None

        if self.__pointer >= len(self.__oracles):
            return None

        if self.__oracles[self.__pointer].current_song() is None:
            # Recursively buzz through the list to see if there are any valid songs. If there aren't,
            # pretend like we never looked in the first place.
            if (len(self.__oracles) > self.__pointer):
                pointer_save = self.__pointer
                self.__pointer += 1
                song = self._inner_get_first_song()
                if song is not None:
                    return song
                self.__pointer -= 1
                #fallthru

            # Same as above - make sure we play the first song of the first oracle if it gets updated before we call
            # next_song()
            self.__oracles.insert(0, PlaylistOracle([]))
            return None

        self.__has_drawn_from_oracle = True
        return self.__oracles[self.__pointer].current_song()

    def add(self, oracle: Union[Oracle, None]):
        if oracle is None:
            return
        self.__oracles.append(oracle)

    def clear(self):
        self.__oracles.clear()
        self.__has_drawn_from_oracle = False


class SwitchOracle(MemoizingOracle):
    """
    Allows switching between multiple oracles.

    This oracle has an edge case where, if you call "next_song()" after setting the first oracle but before
    calling literally anything else, it'll return the first song of that oracle.
    """

    def __init__(self):
        super(SwitchOracle, self).__init__()
        self.__oracle = None

        # We need to make sure we return the first song of an oracle using "current_song()" when calling "next_song()"
        # on the SwitchOracle whenever we switch Oracles. So if you have:
        #    p1, p2  = (PlaylistOracle([1, 2, 3]), PlaylistOracle([4, 5, 6])
        #    switch = SwitchOracle()
        #    switch.set_oracle(p1)
        # and you collect some songs from 'switch' before switching to p2, you'd want the next call to "next_song()" to
        # return "4" instead of "5" (which is what'd be returned by calling 'next_song()' on p2)
        self.__has_gathered_from_oracle = True

        # This one's tricky. If you do something like:
        #   p = PlaylistOracle([1, 2, 3])
        #   o = SwitchOracle()
        #   o.set_oracle(p)
        #   o.next_song()
        # You'd expect it to return "2". BUT: If you instead call:
        #   p = PlaylistOracle(...)
        #   o = SwitchOracle()
        #   o.current_song()
        #   o.set_oracle(p)
        #   o.next_song()
        # You'd expect it to return "1" - meaning that the "None" state acts like it's own Oracle only if it's looked
        # at before assigning an actual Oracle to the SwitchOracle.
        #
        # So: This tracks whether "_get_first_song()" has been called, indicating the second situation, and alters
        # the behavior of _inner_next_song() accordingly.
        #
        # We use a "proscriptive" name here rather than "descriptive" because it's such an effed situation and hopefully
        # any modifiers will look at this comment before breaking the class (although there's a test for this behavior).
        self.__ignore_first_song = True

    def _inner_next_song(self) -> Union[str, None]:
        if self.__oracle is None:
            return None
        if self.__has_gathered_from_oracle or self.__ignore_first_song:
            self.__ignore_first_song = False
            return self.__oracle.next_song()

        song = self.__oracle.current_song()
        self.__has_gathered_from_oracle = True
        return song

    def _inner_get_first_song(self) -> Union[str, None]:
        self.__ignore_first_song = False
        if self.__oracle is None:
            return None
        song = self.__oracle.current_song()
        self.__has_gathered_from_oracle = True
        return song

    def set_oracle(self, oracle: Union[Oracle, None]):
        self.__oracle = oracle
        self.__has_gathered_from_oracle = False


class InterruptOracle(MemoizingOracle):
    """
    Allows interrupting an oracle, then going back to whatever was being done before.
    """

    def __init__(self, default_oracle: Union[Oracle, None]):
        super(InterruptOracle, self).__init__()
        self.__default_oracle = default_oracle
        self._grabbed_first_song = False
        self.__interrupt_oracle = None

    def _inner_next_song(self) -> Union[str, None]:
        if self.__interrupt_oracle is not None:
            # We want to make sure to grab the first song from an oracle when it's interrupting
            # a current oracle before moving onto the second song.
            if not self._grabbed_first_song:
                next_song = self.__interrupt_oracle.current_song()
                self._grabbed_first_song = True
            else:
                next_song = self.__interrupt_oracle.next_song()
            if next_song is not None:
                return next_song

        # If we got here, the interrupt is all out of tunes. Off to the farm with it =(
        self.__interrupt_oracle = None

        if self.__default_oracle is None:
            return None
        return self.__default_oracle.next_song()

    def _inner_get_first_song(self) -> Union[str, None]:
        if self.__interrupt_oracle is not None:
            self._grabbed_first_song = True
            return self.__interrupt_oracle.current_song()
        if self.__default_oracle is None:
            return None
        return self.__default_oracle.current_song()

    def interrupt(self, oracle: Union[Oracle, None]):
        self.__interrupt_oracle = oracle
        self._grabbed_first_song = False

    def clear_interrupt(self):
        self.__interrupt_oracle = None


class RepeatingOracle(Oracle):
    """
    Play a playlist, but forever... or at least the number of "times" passed in initially.
    """

    def __init__(self, playlist: List[str], times=None):
        super(RepeatingOracle, self).__init__()
        self.__playlist = playlist
        # We subtract 1 here because we go through the list once by default before resetting in "next_song".
        # If we didn't, we'd go through the list x+1 times.
        self.times = times - 1 if times is not None else None
        self.__pointer = 0

    def next_song(self) -> Union[str, None]:
        """Guarantees that 'pointer' is always in bounds."""
        if self.__playlist is None:
            return None
        self.__pointer += 1

        # If we have repeat on forever, or we need to repeat and there are repeats left.
        if self.times is None or (self.__pointer >= len(self.__playlist) and self.times > 0):
            self.__pointer = self.__pointer % len(self.__playlist)

            # Sanity check.
            if self.times is not None:
                self.times -= 1

        # No more repetitions.
        if self.__pointer >= len(self.__playlist):
            return None

        return self.__playlist[self.__pointer]

    def current_song(self) -> Union[str, None]:
        if self.__playlist is None or len(self.__playlist) == 0 or self.__pointer >= len(self.__playlist):
            return None
        return self.__playlist[self.__pointer]
