"""
Contains the schema for the V1 CommandServer api - a websockets API used to control the media player remotely.

When operating as intended, the server runs locally on the user's computer, and remote applications connect to
localhost, or other computers in the same local network. Future extensions may change this (e.g. adding control of
the server through a web proxy)

We define the API using only Optional fields, to mitigate errors from minor version changes and prevent field
lock-in as development continues. The server and client are expected to perform validation on each end to ensure
fields are properly set, and handle errors accordingly (which is the expectation when connecting to APIs anyway).

By default, this gets hosted at the "localhost:98210"

All commands and responses get sent via JSON, wrapped in the Command class to differentiate.

As of time of writing (11/30/20) - API is subject to change as development continues.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, List, Protocol

from dataclasses_json import dataclass_json

DEFAULT_PORT = 98210
SERVING_ADDRESS = "/noisebox/command_server/v1"


@dataclass
class Song(object):
    """A song that can be played by the media player."""

    # Human-friendly name of the song - must be unique in a media library, and is used to refer to it elsewhere.
    name: Optional[str]

    # Human-friendly description of the song - only for informational purposes, and maybe un-set.
    description: Optional[str]

    # Additional metadata, currently unspecified.
    metadata: Optional[Any]

    # Path of the file from the viewpoint of the local server.
    local_path: Optional[str]


@dataclass
class Playlist(object):
    """A Playlist of songs that can be played by the media player."""

    # Human-friendly name of the playlist. Picked by the user. It must be unique in a media library, and
    # is used to refer to it elsewhere.
    name: Optional[str]

    # Human-friendly description of the playlist, picked by the user. Informational purposes only.
    description: Optional[str]

    # Additional metadata, currently unspecified.
    metadata: Optional[Any]

    # An ordered list of song aliases - referring to Song.name fields that will play as part of this playlist.
    songs: Optional[List[str]]


class ResponseState(Enum):
    """Different potential response states, indicating the success or failure of the prompting command.

    Should not be instantiated directly.
    """

    def __init__(self):
        raise NotImplementedError

    # Success - the command was performed as-indicated.
    SUCCESS = 0

    # The command has not yet completed. Should be returned in conjunction with a handle to retrieve the status
    # of that command in subsequent commands. Currently unused.
    PENDING = 1

    # Failed successfully - the command failed for normal reasons due to end user error
    USER_ERROR = 2

    # Failed due to client implementation - the command failed because the client code did something wrong.
    CLIENT_ERROR = 3

    # An error caused the process to fail - e.g. IO error, what have you.
    FAILURE = 4

    # Something really went wrong, and failed for an "unexpected" reason resulting in an uncaught exception or the like.
    INTERNAL_ERROR = 5


class CommandCls(Protocol):
    """The protocol defining what a Command payload looks like."""

    # Name of the command to place in the Command.command_name field.
    COMMAND_NAME: str


@dataclass_json
@dataclass
class Command:
    """Wrapper class for all commands."""

    # Required field dictating the command type.
    command_name: Optional[str]

    # Details of the command. Should be set for all commands, but interpreted as an empty object if unset.
    # If set, expected to have the fields of the command type corresponding to the command_name field.
    payload: Optional[CommandCls]


@dataclass_json
@dataclass
class Response:
    """A response that could return error information."""

    # The status of the operation.
    command_status: Optional[ResponseState]

    # A Human-friendly error message, used to understand what happened.
    error_message: Optional[str]

    # Any additional info which might be helpful for debugging. Shape may change depending on the circumstance,
    # server flags, runtime environment, etc etc etc (basically, don't depend on anything in particular)
    error_data: Optional[Any]


@dataclass_json
@dataclass
class TogglePlayCommand:
    """Toggle the play state. Can optionally set the media player to the absolute "play" or "pause" state."""

    COMMAND_NAME = "TOGGLE_PLAY"

    # Optional field which indicates whether the server should play or pause. If unset, the server picks the
    # opposite of the current state.
    play_state: Optional[bool]


@dataclass_json
@dataclass
class TogglePlayResponse(Response):
    """Response to a play command."""

    # Whether media is now playing or not.
    new_play_state: Optional[bool]


@dataclass_json
@dataclass
class NextSongCommand:
    """Skip to the next song."""

    COMMAND_NAME = "NEXT_SONG"


@dataclass_json
@dataclass
class NextSongResponse(Response):
    """Response to a NextSongCommand."""

    # True if a "next" song was found and is now playing.
    still_playing: Optional[bool]

    # May contain the current song playing, or is empty if no song is playing or an error occurred.
    current_song: Optional[str]


@dataclass_json
@dataclass
class ListSongsCommand:
    """Get a list of valid songs to reference."""

    COMMAND_NAME = "LIST_SONGS"

    # Optional token returned by previous ListSong commands
    page_token: Optional[str]

    # Maximum number of responses to return. Actual number may be smaller, depending on songs available etc.
    max_num_entries: Optional[int] = 30


@dataclass_json
@dataclass
class ListSongsResponse(Response):
    """The list of currently available songs."""

    # The list of songs being returned
    songs: Optional[List[Song]]

    # Token for future "ListSong" commands to pick up at the same spot.
    page_token: Optional[str]


@dataclass_json
@dataclass
class ListPlaylistsCommand:
    """Get a list of valid playlists to reference."""

    COMMAND_NAME = "LIST_PLAYLISTS"

    # Optional token returned by previous ListPlaylists commands.
    page_token: Optional[str]

    # Maximum number of responses to return. Actual number may be smaller, depending on songs available etc.
    max_num_entries: Optional[int] = 30


@dataclass_json
@dataclass
class ListPlaylistCommand(Response):
    """The list of the currently available playlists."""

    # The list of playlists being returned.
    playlists: Optional[List[Playlist]]

    # Token for future "ListPlaylists" commands to pick up at the same spot.
    page_token: Optional[str]
