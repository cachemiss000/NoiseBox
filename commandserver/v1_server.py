import collections
from enum import Enum

from typing import List, Tuple, Optional

import commandserver.command_types_v1 as c_types
from commandserver import server_flags as server_flags
from medialogic import media_library, controller
from common import flags

VERSION = "V1"
FLAGS = flags.FLAGS
FLAGS.register_flags(server_flags.flags)

# TODO: For type sanity, this NEEDS to be a class. Goddamn.
Page = collections.namedtuple("Page", ["list_hash", "element"])


class OutdatedPageException(Exception):
    pass


class ErrorDataType(Enum):
    """Dictates what kind of error data is attached to an exception.

    Used for scrubbing debug data when debug is false.
    """

    # Running out in the wild. Scrub debug data.
    PRODUCTION: int = 0

    # Running in dev mode. Keep debug data.
    DEBUG: int = 1


class ErrorResponse(Exception, c_types.Response):

    def __init__(self, error_data_type=ErrorDataType.DEBUG, **kwargs):
        """Really gross manual initialization of base classes.

         This ensures the Exception class gets the error message.

         Also removes error_data if it contains Debug data.
         """
        if error_data_type == ErrorDataType.DEBUG and not FLAGS.debug:
            kwargs.pop("error_data", None)

        Exception.__init__(self, kwargs.get("error_message"))
        c_types.Response.__init__(self, **kwargs)


# Command names in this list do not need a parameter list to execute successfully, and will
# not be checked for them by the command validation code.
PARAMETERLESS_COMMANDS: List[str] = [
    c_types.TogglePlayCommand.COMMAND_NAME,
    c_types.NextSongCommand.COMMAND_NAME,
    c_types.ListSongsCommand.COMMAND_NAME,
    c_types.ListPlaylistsCommand.COMMAND_NAME,
]


class MediaServer:
    def __init__(self, c: controller.Controller, ml: media_library.MediaLibrary):
        super(MediaServer, self).__init__()
        self.media_library = ml
        self.controller = c

    @classmethod
    def parse_command(cls, command: str) -> c_types.Command:
        """Parses a JSON command from the input string as expected over a raw websocket."""
        # infer_missing returns missing fields as None, which is always the desired behavior
        # in our case. Otherwise, empty optional fields would throw.
        command_result = c_types.Command.from_json(command, infer_missing=True)  # type: ignore
        if command_result.command_name is None:
            raise ErrorResponse(command_status=c_types.CommandStatus.CLIENT_ERROR,
                                error_message="Command name must be specified on the input command",
                                error_data=command,
                                error_data_type=ErrorDataType.DEBUG)

        if command_result.command_name not in c_types.COMMAND_NAMES:
            raise ErrorResponse(command_status=c_types.CommandStatus.CLIENT_ERROR,
                                error_message="Command name '%s' is not a valid %s command" % (
                                    command_result.command_name, VERSION),
                                error_data=command,
                                error_data_type=ErrorDataType.DEBUG)

        if command_result.command_name in PARAMETERLESS_COMMANDS:
            return command_result  # No error checking needed if it otherwise parsed correctly.

        if command_result.payload is None:
            raise ErrorResponse(command_status=c_types.CommandStatus.CLIENT_ERROR,
                                error_message="Payload expected for command '%s'" % (command_result.command_name,),
                                error_data=command)
        return command_result

    def accept(self, command_str: str) -> c_types.Response:
        try:
            command = MediaServer.parse_command(command_str)
            if command.command_name == c_types.TogglePlayCommand.COMMAND_NAME:
                return self.toggle_play(
                    c_types.TogglePlayCommand.from_dict(command.payload) if command.payload else None)  # type: ignore
        except ErrorResponse as e:
            return e
        except Exception as e:
            return ErrorResponse(
                command_status=c_types.CommandStatus.INTERNAL_ERROR,
                error_message="Unexpected error encountered: '%s'" % (e,),
                error_data=e)
        return ErrorResponse(
            command_status=c_types.CommandStatus.INTERNAL_ERROR,
            error_message="Unexpected error encountered.")

    def toggle_play(self, play_request: Optional[c_types.TogglePlayCommand]) -> c_types.Response:
        """Toggles the play/pause state, with "play" == True.

        This contrasts with VLC's interpretation, where "pause" == True, which is standard further down
        the stack.
        """
        if play_request is None or play_request.play_state is None:
            self.controller.toggle_pause()
            return c_types.TogglePlayResponse(new_play_state=self.controller.playing(),
                                              command_status=c_types.CommandStatus.SUCCESS)

        # Invert play_state because we're setting the pause value.
        # Vlc has some weird semantics. I refuse to build around them at this level.
        self.controller.set_pause(not play_request.play_state)

        return c_types.TogglePlayResponse(new_play_state=self.controller.playing(),
                                          command_status=c_types.CommandStatus.SUCCESS)

    #
    # def ListSongs(self, list_songs_request: ms_pb.ListSongsRequest, ctx) -> ms_pb.ListSongsResponse:
    #     songs = self.media_library.list_songs()
    #
    #     if list_songs_request.max_num_entries:
    #         max_response_size = list_songs_request.max_num_entries
    #     else:
    #         max_response_size = DEFAULT_MAX_RESPONSE_SIZE
    #     next_page, next_page_token = get_output_page(songs, max_response_size,
    #                                                  string_to_page(list_songs_request.page_token))
    #     response = ms_pb.ListSongResponse()
    #     response.song_names.extend(next_page)
    #     response.next_page_token = page_to_string(next_page_token)
    #     return response
    #
    # def add_to_server(self, server: grpc.Server):
    #     ms_pb_grpc.add_MediaControlServiceServicer_to_server(self, server)
    #
    # def ListPlaylists(self, list_playlists_request: ms_pb.ListPlaylistsRequest, ctx) -> ms_pb.ListPlaylistsResponse:
    #     playlist_tuples = self.media_library.list_playlists()
    #     # Playlist tuples have two entries: The playlist name, then a list of all songs in the playlist.
    #     # TODO: Playlists should be a class, just like songs.
    #     playlists = (pt[0] for pt in playlist_tuples)
    #
    #     if list_playlists_request.max_num_entries:
    #         max_response_size = list_playlists_request.max_num_entries
    #     else:
    #         max_response_size = DEFAULT_MAX_RESPONSE_SIZE
    #
    #     next_page, next_page_token = get_output_page(list(playlists), max_response_size,
    #                                                  string_to_page(list_playlists_request.page_token))
    #     response = ms_pb.ListPlaylistsResponse()
    #     response.playlist_names.extend(next_page)
    #     response.next_page_token = page_to_string(next_page_token)
    #     return response
    #


def get_output_page(sequence: List[object],
                    max_length: int,
                    next_page_token: Optional[Page]) -> Tuple[List[object], Optional[Page]]:
    # Quick little cheat so we can use this code even when no page was provided.
    sequence_hash = str(hash(tuple(sequence)))
    if not next_page_token:
        next_page_token = Page(list_hash=sequence_hash, element=0)
    if next_page_token.list_hash != sequence_hash:
        raise OutdatedPageException("List has been updated since last page was retrieved")
    first_element = int(next_page_token.element)
    next_page_start = first_element + max_length
    next_page = sequence[first_element:next_page_start]
    next_page_token = None
    if next_page_start < len(sequence):
        next_page_token = Page(list_hash=sequence_hash, element=next_page_start)
    return next_page, next_page_token


def page_to_string(page: Page) -> str:
    if not page:
        return ""
    string = "%s|%s" % (page.list_hash, page.element)
    return bytearray(string, "ascii").hex()


def string_to_page(hex_string: str) -> Optional[Page]:
    if not hex_string:
        return None

    string = bytearray.fromhex(hex_string).decode()
    tuple = string.split("|")
    return Page(list_hash=tuple[0], element=tuple[1])
