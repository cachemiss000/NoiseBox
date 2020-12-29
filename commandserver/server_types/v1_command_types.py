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
import abc
import json
import logging
from enum import Enum, IntEnum
from pathlib import Path
from typing import Optional, List, Type, Dict, Union, cast, ClassVar, Set, TypeVar, Protocol, get_args

from pydantic import Field, validator
from pydantic.dataclasses import dataclass
from pydantic.main import BaseModel

from common.utils import class_name

VERSION = 'v1'

DEFAULT_PORT = 9821
SERVING_ADDRESS = "/noisebox/command_server/v1"

logger = logging.getLogger('%s_schema' % (VERSION,))


@dataclass
class MessageObj(Protocol):
    @abc.abstractmethod
    def wrap(self) -> "Message":
        """Wrap any potential base message in the Message container"""
        pass

    @abc.abstractmethod
    def unwrap(self, message_type: Type["Types.P_T"]) -> "Types.P_T":
        """Unwrap some message to it's base type, either a command or an event"""
        pass


class Song(BaseModel):
    """A song that can be played by the media player."""

    name: Optional[str] = Field(
        description="Human-friendly name of the song - must be unique in a media library, "
                    "and is used to refer to it elsewhere.")

    description: Optional[str] = Field(
        description="Human-friendly description of the song - only for informational purposes, and maybe un-set.")

    metadata: Optional[Dict[str, str]] = Field(description="Additional key-value metadata, currently unspecified.")

    local_path: Optional[str] = Field(description="Path of the file from the viewpoint of the local server.")


class Playlist(BaseModel):
    name: Optional[str] = Field(
        description="Human-friendly name of the playlist. Picked by the user. It must be unique in a media library, and"
                    "is used to refer to it elsewhere.")

    description: Optional[str] = Field(
        description="Human-friendly description of the playlist, picked by the user. Informational purposes only.")

    metadata: Optional[Dict[str, str]] = Field(
        description="Human-friendly description of the playlist, picked by the user. Informational purposes only.")

    songs: Optional[List[str]] = Field(
        description="An ordered list of song aliases - referring to Song.name fields that will play "
                    "as part of this playlist.")


class ErrorType(IntEnum):
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


class Message(BaseModel):
    event: Optional["Types.EVENT_TYPES"] = Field(description="Describes something that happened to a client or server. "
                                                             "Mutually exclusive with the 'command' field.")
    command: Optional["Types.COMMAND_TYPES"] = Field(description="Describes something that the server should do. "
                                                                 "Mutually exclusive with the 'event' field.")

    @validator("command", always=True)
    def ensure_one_of_command_or_event_set(cls, v, values):
        """Ensure only command or event is set

        WILL get messed up if 'command' gets put before 'event' in the field definitions, because validators
        run such that 'values' only contains previously-defined fields.
        """
        if values.get('event', None) and v:
            raise ValueError("Cannot set both command and event in a message.")
        if not values.get('event', None) and not v:
            raise ValueError("Must set at least one of 'event' and 'command'. Got '%s'" % (values,))
        return v

    def unwrap(self, payload_t: Type["Types.P_T"]) -> "Types.P_T":
        if self.command:
            if not issubclass(payload_t, Command):
                raise TypeError("Cannot unwrap Command value '%s' to non-command type %s" % (class_name(self.command),
                                                                                             class_name(payload_t)))
            return cast(Types.P_T, self.command.unwrap(payload_t))
        if self.event:
            if not issubclass(payload_t, Event):
                raise TypeError("Cannot unwrap Event value '%s' to non-event type %s" % (class_name(self.event),
                                                                                         class_name(payload_t)))
            return cast(Types.P_T, self.event.unwrap(payload_t))
        raise ValueError("Event must be defined if command is not. \n"
                         "Should have been checked by @validator functions.\nFor msg %s" % (self,))

    def wrap(self) -> "Message":
        return self

    def is_type(self, payload_t: Type["Types.P_T"]) -> bool:
        if isinstance(self.event, payload_t):
            return True
        if isinstance(self.command, payload_t):
            return True
        return False

    def get_error(self) -> Optional["ErrorEvent"]:
        if self.is_type(ErrorEvent):
            return cast(ErrorEvent, self.unwrap(ErrorEvent))
        return None

    def json(self, *args, **kwargs):
        kwargs['exclude_unset'] = True
        return super(Message, self).json(*args, **kwargs)


class Command(BaseModel):
    """The protocol defining what a Command payload looks like.

    All commands subclass CommandCls.
    """
    COMMAND_NAME_FIELD_DESC: ClassVar[str] = "Command sub-type - e.g. the command to perform."
    COMMAND_NAME: ClassVar[str]  # Must have ClassVar type info in every subclass instance.
    command_name: str

    @classmethod
    def create(cls: Type["Types.C_T"], **data) -> "Types.C_T":
        data.update({"command_name": cls.COMMAND_NAME})
        return cls(**data)

    @validator('command_name', pre=True, always=True)
    def ensure_valid_command_name(cls, this_command_name: str):
        command_names = set(c.COMMAND_NAME for c in COMMANDS)
        if not this_command_name:
            raise ValueError("command_name unset")
        if this_command_name not in command_names:
            raise ValueError("Could not find command name '%s' in possible command names: [%s]" % (
                this_command_name, ", ".join(command_names)))
        return this_command_name

    def unwrap(self, command_t: Type["Types.P_T"]) -> "Types.P_T":
        if not issubclass(command_t, Command):
            raise TypeError(
                "Expected Command to unwrap to a subclass of Command, instead got '%s'" % (class_name(command_t),))

        if self.command_name != command_t.COMMAND_NAME:
            raise TypeError(
                "Trying to unwrap '%s' to incompatable type %s" % (class_name(self), class_name(command_t)))

        return cast(Types.P_T, self)

    def wrap(self) -> Message:
        assert any(isinstance(self, t) for t in COMMANDS), "Expected command type %s to be in '%s'" % (
            class_name(self), (class_name(t) for t in COMMANDS))
        # noinspection PyTypeChecker
        return Message(command=self, event=None)


class Event(BaseModel):
    """The protocol defining what an Event payload looks like.

    All events subclass EventCls.
    """
    EVENT_NAME: ClassVar[str]
    EVENT_NAME_FIELD_DESC: ClassVar[str] = "Command sub-type - e.g. the command to perform."
    event_name: str

    @validator('event_name', pre=True, always=True)
    def ensure_valid_event_name(cls, this_event_name: str):
        event_names = set(e.EVENT_NAME for e in EVENTS)
        if not this_event_name:
            raise ValueError("event_name unset")
        if this_event_name not in event_names:
            raise ValueError("could not find event name '%s' in possible event names: [%s]" % (
                this_event_name, ", ".join(event_names)))
        return this_event_name

    def unwrap(self, event_t: Type["Types.P_T"]) -> "Types.P_T":
        if not issubclass(event_t, Event):
            raise TypeError(
                "expected Command to unwrap to a subclass of Command, instead got '%s'" % (class_name(event_t),))

        if self.event_name != event_t.EVENT_NAME:
            raise TypeError(
                "trying to unwrap '%s' to incompatable type %s" % (class_name(self), class_name(event_t)))

        return cast(Types.P_T, self)

    def wrap(self) -> Message:
        assert any(isinstance(self, t) for t in EVENTS), "Expected event type %s to be in '%s'" % (
            class_name(self), ", ".join(class_name(t) for t in EVENTS))
        # noinspection PyTypeChecker
        return Message(event=self, command=None)

    @classmethod
    def create(cls: Type["Types.E_T"], **data) -> "Types.E_T":
        data.update({"event_name": cls.EVENT_NAME})
        return cls(**data)


class ErrorDataEnv(Enum):
    """Dictates what kind of error data is attached to an exception.

    Used to indicate to the viewer whether debug data has been scrubbed. If a programmer sees "data_env=DEBUG"
    and no debug data, that will result in a very different debug process than if they see "data_env=PROD" and
    no debug data - so it's worth keeping around even if it's merely descriptive (rather than proscriptive) and
    self-evident 99% of the time to boot.

    Attributes:
        ErrorDataEnv.PRODUCTION: Running out in the wild. Scrub debug data.
        ErrorDataEnv.DEBUG: Running in dev mode. Keep debug data.
    """
    PRODUCTION: int = 0
    DEBUG: int = 1


class EventException(Exception):
    """Throw an ErrorEvent (below) as an exception - cannot use inheritance because of the BaseModel subclass."""

    def __init__(self, error_event: "ErrorEvent"):
        self.error_event = error_event


class ErrorEvent(Event):
    """Something bad happened and the guy on the other end of the wire needs to know about it.

    TODO: This should get added to a generic, versionless schema, then separately copied into the V1 schema.
    """

    EVENT_NAME: ClassVar[str] = "ERROR"
    event_name: str = Field(regex=EVENT_NAME, description=Event.EVENT_NAME_FIELD_DESC)

    error_message: Optional[str] = Field(default="",
                                         description="The user-friendly error message. Should always get set.", )

    error_type: Optional[ErrorType] = Field(
        description='The type of error - e.g. "USER", or "INTERNAL" or whatever. Hints at where to look,'
                    ' and whether it\'ll get fixed if whatever caused it is tried again.'
    )

    error_data: Optional[str] = Field(
        description="The dev- and machine-friendly error data. May not be set for production builds.")

    error_env: Optional[Union[ErrorDataEnv, int]] = Field(
        default=ErrorDataEnv.DEBUG,
        description="Whether the return data is targeted for a dev- or prod- environment")

    originating_command: Optional[str] = Field(
        description="The dev- and machine-friendly command that originated this event. May not be set in "
                    "production builds. May not be set for errors that had no contributing event. May "
                    "be a string for commands that weren't fully parsed.")

    def for_prod(self) -> "ErrorEvent":
        error_message = "Unxpected error encountered." \
            if self.error_type == ErrorType.INTERNAL_ERROR else self.error_message

        return ErrorEvent.create(error_message=error_message, error_type=self.error_type,
                                 error_env=ErrorDataEnv.PRODUCTION)

    def exception(self) -> EventException:
        return EventException(self)


class TogglePlayCommand(Command):
    """Toggle the play state. Can optionally set the media player to the absolute "play" or "pause" state."""
    COMMAND_NAME: ClassVar[str] = "TOGGLE_PLAY"
    command_name: str = Field(regex=COMMAND_NAME, description=Command.COMMAND_NAME_FIELD_DESC)

    play_state: Optional[bool] = Field(
        description="Optional field which indicates whether the server should play or pause. If unset, the server "
                    "picks the opposite of the current state.")


class PlayStateEvent(Event):
    """Tells the client whether the media player is playing or not.."""
    EVENT_NAME: ClassVar[str] = "PLAY_STATE"
    event_name: str = Field(regex=EVENT_NAME, description=Event.EVENT_NAME_FIELD_DESC)

    new_play_state: Optional[bool] = Field(description="Whether media is now playing or not.")


class NextSongCommand(Command):
    """Skip to the next song."""
    COMMAND_NAME: ClassVar[str] = "NEXT_SONG"
    command_name: str = Field(regex=COMMAND_NAME, description=Command.COMMAND_NAME_FIELD_DESC)


class SongPlayingEvent(Event):
    """Informs the client that a new song is currently playing."""
    EVENT_NAME: ClassVar[str] = "SONG_PLAYING"
    event_name: str = Field(regex=EVENT_NAME, description=Event.EVENT_NAME_FIELD_DESC)

    current_song: Optional[Song] = Field(description="Info for the current song")


class ListSongsCommand(Command):
    """Get a list of valid songs to reference."""
    COMMAND_NAME: ClassVar[str] = "LIST_SONGS"
    command_name: str = Field(regex=COMMAND_NAME, description=Command.COMMAND_NAME_FIELD_DESC)


class ListSongsEvent(Event):
    """Client receives a list of songs, usually by request."""
    EVENT_NAME: ClassVar[str] = "LIST_SONGS"
    event_name: str = Field(regex=EVENT_NAME, description=Event.EVENT_NAME_FIELD_DESC)

    songs: Optional[List[Song]] = Field(description="The list of songs being returned")


class ListPlaylistsCommand(Command):
    """Get a list of valid playlists to reference."""

    COMMAND_NAME: ClassVar[str] = "LIST_PLAYLISTS"
    command_name: str = Field(regex=COMMAND_NAME, description=Command.COMMAND_NAME_FIELD_DESC)


class ListPlaylistsEvent(Event):
    """Client receives a list of playlists, usually by request."""
    EVENT_NAME: ClassVar[str] = "LIST_PLAYLISTS"
    event_name: str = Field(regex=EVENT_NAME, description=Event.EVENT_NAME_FIELD_DESC)

    playlists: Optional[List[Playlist]] = Field(descrption="The list of playlists being returned.")


class Types:
    EVENT_TYPES = Union[ErrorEvent, PlayStateEvent, SongPlayingEvent, ListSongsEvent, ListPlaylistsEvent]
    COMMAND_TYPES = Union[TogglePlayCommand, NextSongCommand, ListSongsCommand, ListPlaylistsCommand]
    OBJECT_TYPES = Union[Song, Playlist, Event, Command, Message]

    P_T = TypeVar('P_T', Event, Command)
    E_T = TypeVar('E_T', bound=Event)
    C_T = TypeVar('C_T', bound=Command)


COMMANDS: Set[Type[Command]] = {t for t in get_args(Types.COMMAND_TYPES)}
EVENTS: Set[Type[Event]] = {t for t in get_args(Types.EVENT_TYPES)}
OBJECTS: Set[Type[BaseModel]] = {t for t in get_args(Types.OBJECT_TYPES)}
_IGNORE_OBJECTS: Set[Type[object]] = {ErrorType, ErrorDataEnv, EventException, Types, MessageObj}


def update_fwd_refs():
    for c in COMMANDS:
        c.update_forward_refs()
    for e in EVENTS:
        e.update_forward_refs()
    for o in OBJECTS:
        o.update_forward_refs()


update_fwd_refs()


def print_schema(base_dir: str):
    """Write out the JSON schemas for this version's schema to a corresponding subdirectory."""
    out_dir = Path(base_dir).joinpath(VERSION)
    out_dir.mkdir(exist_ok=True)
    logger.info("printing files to: %s" % (Path(out_dir).joinpath('...'),))
    for object_cls in OBJECTS:
        print_to_file(out_dir, object_cls.__name__, json.dumps(object_cls.schema(), indent=4))
    for command_cls in COMMANDS:
        print_to_file(out_dir, command_cls.__name__, json.dumps(command_cls.schema(), indent=4))
    for response_cls in EVENTS:
        print_to_file(out_dir, response_cls.__name__, json.dumps(response_cls.schema(), indent=4))
    logger.info("finished writing.")


def print_to_file(out_dir, name, contents):
    with open(Path(out_dir.joinpath(name + '.json')), mode='w+t') as file:
        file.write(contents)


def prettify_message(msg: Optional[Union[str, "MessageObj"]]) -> str:
    if not msg:
        return ""
    if isinstance(msg, str):
        msg = Message.parse_raw(msg)
    return msg.wrap().json().encode('latin1').decode('unicode_escape')
