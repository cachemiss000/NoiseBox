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
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Set, Type, Dict, Union, cast

from dataclasses_json import dataclass_json
from dataclasses_jsonschema import JsonSchemaMixin

from messages.message_map import Message, MessageCls, message_map, MessageMapTypeHints, Types

VERSION = 'v1'

DEFAULT_PORT = 98210
SERVING_ADDRESS = "/noisebox/command_server/v1"

logger = logging.getLogger('%s_schema' % (VERSION,))


@dataclass_json
@dataclass
class Song(JsonSchemaMixin):
    """A song that can be played by the media player."""

    # Human-friendly name of the song - must be unique in a media library, and is used to refer to it elsewhere.
    name: Optional[str]

    # Human-friendly description of the song - only for informational purposes, and maybe un-set.
    description: Optional[str] = None

    # Additional key-value metadata, currently unspecified.
    metadata: Optional[Dict[str, str]] = None

    # Path of the file from the viewpoint of the local server.
    local_path: Optional[str] = None


@dataclass_json
@dataclass
class Playlist(JsonSchemaMixin):
    """A Playlist of songs that can be played by the media player."""

    # Human-friendly name of the playlist. Picked by the user. It must be unique in a media library, and
    # is used to refer to it elsewhere.
    name: Optional[str]

    # Human-friendly description of the playlist, picked by the user. Informational purposes only.
    description: Optional[str] = None

    # Additional key-value metadata, currently unspecified.
    metadata: Optional[Dict[str, str]] = None

    # An ordered list of song aliases - referring to Song.name fields that will play as part of this playlist.
    songs: Optional[List[str]] = None


class ErrorType(Enum):
    """Different potential response states, indicating the success or failure of the prompting command.

    Should not be instantiated directly.
    """

    # Failed successfully - the command failed for normal reasons due to end user error
    USER_ERROR = 0

    # Failed due to client implementation - the command failed because the client code did something wrong.
    CLIENT_ERROR = 1

    # An error caused the process to fail - e.g. IO error, what have you.
    FAILURE = 2

    # Something really went wrong, and failed for an "unexpected" reason resulting in an uncaught exception or the like.
    INTERNAL_ERROR = 3


class CommandCls(MessageCls, JsonSchemaMixin):
    """The protocol defining what a Command payload looks like.

    All commands subclass CommandCls.
    """
    def wrap(self) -> "Command":
        return Command(message_name=self.MESSAGE_NAME, payload=self)

    def unwrap(self, command_t: Type["Types.M_C"]) -> "Types.M_C":
        return cast(Types.M_C, super(CommandCls, self).unwrap(command_t))


class EventCls(MessageCls, JsonSchemaMixin):
    """The protocol defining what an Event payload looks like.

    All events subclass EventCls.
    """

    def for_prod(self) -> "EventCls":
        return self

    def wrap(self) -> "Event":
        return Event(message_name=self.MESSAGE_NAME, payload=self)

    def unwrap(self, event_t: Type["Types.M_C"]) -> "Types.M_C":
        return cast(Types.M_C, super(EventCls, self).unwrap(event_t))


@dataclass_json
@dataclass
class Command(Message):
    """A command is an instruction to do something. Servers receive commands, and then act on them.

    Commands include things like "stop playing", "go to the next song", "create a new playlist", whatever.
    """
    def wrap(self) -> "Command":
        return self

    def unwrap(self, command_t: Type["Types.M_C"]) -> "Types.M_C":
        return cast(Types.M_C, super(Command, self).unwrap(command_t))


@dataclass_json
@dataclass
class Event(Message):
    """An event is information about the world, or something that happened. Clients receive events.

    For instance, an event could include error information about the session, it could contain new
    information about the player's state, it could contain requested information like "playlist names" or
    "song names", and so on.

    These are *generally* issued in response to commands, but not always. It's expected that components on
    the client side hook themselves up to events they care about - e.g. list boxes to 'list playlist' events
    and what have you.
    """
    def wrap(self) -> "Event":
        return self

    def unwrap(self, event_t: Type["Types.M_C"]) -> "Types.M_C":
        return cast(Types.M_C, super(Event, self).unwrap(event_t))


class ErrorDataEnv(Enum):
    """Dictates what kind of error data is attached to an exception.

    Used to indicate to the viewer whether debug data has been scrubbed. If a programmer sees "data_env=DEBUG"
    and no debug data, that will result in a very different debug process than if they see "data_env=PROD" and
    no debug data - so it's worth keeping around even if it's merely descriptive (rather than proscriptive) and
    self-evident 99% of the time to boot.
    """

    # Running out in the wild. Scrub debug data.
    PRODUCTION: int = 0

    # Running in dev mode. Keep debug data.
    DEBUG: int = 1


@dataclass_json
@dataclass
class ErrorEvent(EventCls, Exception):
    """Something bad happened and the guy on the other end of the wire needs to know about it.

    TODO: This should get added to a generic, versionless schema, then separately copied into the V1 schema.
    """

    MESSAGE_NAME = "ERROR"

    # The user-friendly error message. Should always get set.
    error_message: Optional[str] = None

    # The type of error - e.g. "USER", or "INTERNAL" or whatever. Hints at where to look,
    # and whether it'll get fixed if whatever caused it is tried again.
    error_type: Optional[ErrorType] = None

    # The dev- and machine-friendly error data. May not be set for production builds.
    error_data: Optional[str] = None

    # Whether the return data is targeted for a dev- or prod- environment
    error_env: Optional[Union[ErrorDataEnv, int]] = ErrorDataEnv.DEBUG

    # The dev- and machine-friendly command that originated this event. May not be set in
    # production builds. May not be set for errors that had no contributing event. May
    # be a string for commands that weren't fully parsed.
    originating_command: Optional[str] = None

    def for_prod(self) -> "ErrorEvent":
        return ErrorEvent(error_message=self.error_message, error_type=self.error_type,
                          error_env=ErrorDataEnv.PRODUCTION)


@dataclass_json
@dataclass
class TogglePlayCommand(CommandCls):
    """Toggle the play state. Can optionally set the media player to the absolute "play" or "pause" state."""

    MESSAGE_NAME = "TOGGLE_PLAY"

    # Optional field which indicates whether the server should play or pause. If unset, the server picks the
    # opposite of the current state.
    play_state: Optional[bool] = None


@dataclass_json
@dataclass
class PlayStateEvent(EventCls):
    """Tells the client whether the media player is playing or not.."""

    MESSAGE_NAME = "PLAY_STATE"

    # Whether media is now playing or not.
    new_play_state: Optional[bool] = None


@dataclass_json
@dataclass
class NextSongCommand(CommandCls):
    """Skip to the next song."""

    MESSAGE_NAME = "NEXT_SONG"


@dataclass_json
@dataclass
class SongPlayingEvent(EventCls):
    """Informs the client that a new song is currently playing."""

    MESSAGE_NAME = "SONG_PLAYING"

    # Info for the current song
    current_song: Optional[Song] = None


@dataclass_json
@dataclass
class ListSongsCommand(CommandCls):
    """Get a list of valid songs to reference."""

    MESSAGE_NAME = "LIST_SONGS"


@dataclass_json
@dataclass
class ListSongsEvent(EventCls):
    """Client receives a list of songs, usually by request."""

    MESSAGE_NAME = "LIST_SONGS"

    # The list of songs being returned
    songs: Optional[List[Song]] = None


@dataclass_json
@dataclass
class ListPlaylistsCommand(CommandCls):
    """Get a list of valid playlists to reference."""

    MESSAGE_NAME = "LIST_PLAYLISTS"


@dataclass_json
@dataclass
class ListPlaylistsEvent(EventCls):
    """Client receives a list of playlists, usually by request."""

    MESSAGE_NAME = "LIST_PLAYLISTS"

    # The list of playlists being returned.
    playlists: Optional[List[Playlist]] = None


def print_schema(base_dir: str):
    """Write out the JSON schemas for this version's schema to a corresponding subdirectory."""
    out_dir = Path(base_dir).joinpath(VERSION)
    out_dir.mkdir(exist_ok=True)
    logger.info("printing files to: %s" % (Path(out_dir).joinpath('...'),))
    for object_cls in OBJECTS:
        print_to_file(out_dir, object_cls.__name__, json.dumps(object_cls.json_schema(), indent=4))
    for command_cls in COMMANDS:
        print_to_file(out_dir, command_cls.__name__, json.dumps(command_cls.json_schema(), indent=4))
    for response_cls in EVENTS:
        print_to_file(out_dir, response_cls.__name__, json.dumps(response_cls.json_schema(), indent=4))
    logger.info("finished writing.")


def print_to_file(out_dir, name, contents):
    with open(Path(out_dir.joinpath(name + '.json')), mode='w+t') as file:
        file.write(contents)


OBJECTS: Set[Type[JsonSchemaMixin]] = {Song, Playlist}
COMMANDS: Set[Type[CommandCls]] = {TogglePlayCommand, NextSongCommand, ListSongsCommand, ListPlaylistsCommand}
EVENTS: Set[Type[EventCls]] = {PlayStateEvent, SongPlayingEvent, ListSongsEvent, ListPlaylistsEvent, ErrorEvent}


@message_map(message_name="event", message_types=EVENTS)
class EventTypeMap(MessageMapTypeHints[Event, EventCls]):
    """Superclass for classes which want to handle "Event" messages.

    Clients should override "with_<event_name_>(...)" functions as described in 'messages.message_map.message_handler()'

    ex: To handle PlayStateEvent's, implement
      def with_play_state(ps_event: PlayStateEvent) -> Any:
        ....

    You can call "expect_<event_name>(handler: message_maps.Types.MessageHandler)" to get a quick and dirty one-event
    EventTypeMap.
    """
    pass


@message_map(message_name="command", message_types=COMMANDS)
class CommandTypeMap(MessageMapTypeHints[Command, CommandCls]):
    """See the EventTypeMap class documentation. This is the same, except substitute "event" with "command"."""
    pass


"""
BOOK KEEPING OBJECTS:
  These objects work to keep track of all the classes defined in this file. It's expected that, if you add new commands
  or events, you update these dicts accordingly. The schema auto-generation stuff uses these variables to keep track
  of what does and doesn't need schemas generated for them. 
"""
_IGNORE_OBJECTS: Set[Type[object]] = {ErrorType, CommandCls, Command, Event, EventCls, ErrorDataEnv, CommandTypeMap,
                                      EventTypeMap}

COMMAND_NAMES: Set[str] = set(map(lambda x: x.MESSAGE_NAME, COMMANDS))
EVENT_NAMES: Set[str] = set(map(lambda x: x.MESSAGE_NAME, EVENTS))
EVENT_NAME_CLS_MAP: Dict[str, Type[EventCls]] = {event.MESSAGE_NAME: event for event in EVENTS}
