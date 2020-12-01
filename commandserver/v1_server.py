import collections
import websockets
import json
from typing import List, Tuple

import commandserver.command_types_v1 as c_types
from medialogic import media_library, controller


DEFAULT_MAX_RESPONSE_SIZE = 200

# TODO: For type sanity, this NEEDS to be a class. Goddamn.
Page = collections.namedtuple("Page", ["list_hash", "element"])


class OutdatedPageException(Exception):
    pass


class ErrorResponse(Exception, c_types.Response):
    pass


# Command names in this list do not need a parameter list to execute successfully, and will
# not be checked for them by the command validation code.
PARAMETERLESS_COMMANDS = [
    c_types.TogglePlayCommand.COMMAND_NAME,
    c_types.NextSongCommand.COMMAND_NAME,
    c_types.ListSongs.COMMAND_NAME,
    c_types.ListPlaylistsCommand.COMMAND_NAME,
]


class MediaServer:
    def __init__(self, controller: controller.Controller, media_library: media_library.MediaLibrary):
        super(MediaServer, self).__init__()
        self.media_library = media_library
        self.controller = controller

    @classmethod
    def parse_command(cls, command: str) -> c_types.Command:
        """Parses a JSON command from the input string as expected over a raw websocket."""
        json_result = c_types.Command.from_json(command)
        if json_result.command_name is None:
            raise ErrorResponse(command_status=c_types.ResponseState.CLIENT_ERROR,
                                error_message="Command name must be specified on the input command",
                                error_data=command)

        if json_result.command_name in PARAMETERLESS_COMMANDS:
            return  # No error checking needed if it otherwise parsed correctly.

        if json_result.payload is None:
            raise ErrorResponse(command_status=c_types.ResponseState.CLIENT_ERROR,
                                error_message="Payload expected for command '%s'" % (json_result.command_name,),
                                error_data=command)




    def Play(self, play_request, context) -> ms_pb.PlayResponse:
        self.controller.resume()
        return ms_pb.PlayResponse()

    def ListSongs(self, list_songs_request: ms_pb.ListSongsRequest, ctx) -> ms_pb.ListSongsResponse:
        songs = self.media_library.list_songs()

        if list_songs_request.max_num_entries:
            max_response_size = list_songs_request.max_num_entries
        else:
            max_response_size = DEFAULT_MAX_RESPONSE_SIZE
        next_page, next_page_token = get_output_page(songs, max_response_size,
                                                     string_to_page(list_songs_request.page_token))
        response = ms_pb.ListSongResponse()
        response.song_names.extend(next_page)
        response.next_page_token = page_to_string(next_page_token)
        return response

    def add_to_server(self, server: grpc.Server):
        ms_pb_grpc.add_MediaControlServiceServicer_to_server(self, server)

    def ListPlaylists(self, list_playlists_request: ms_pb.ListPlaylistsRequest, ctx) -> ms_pb.ListPlaylistsResponse:
        playlist_tuples = self.media_library.list_playlists()
        # Playlist tuples have two entries: The playlist name, then a list of all songs in the playlist.
        # TODO: Playlists should be a class, just like songs.
        playlists = (pt[0] for pt in playlist_tuples)

        if list_playlists_request.max_num_entries:
            max_response_size = list_playlists_request.max_num_entries
        else:
            max_response_size = DEFAULT_MAX_RESPONSE_SIZE

        next_page, next_page_token = get_output_page(list(playlists), max_response_size,
                                                     string_to_page(list_playlists_request.page_token))
        response = ms_pb.ListPlaylistsResponse()
        response.playlist_names.extend(next_page)
        response.next_page_token = page_to_string(next_page_token)
        return response


def get_output_page(sequence: List[object], max_length: int, next_page_token: Page) -> Tuple[List[object], Page]:
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


def string_to_page(hex_string: str) -> Page:
    if not hex_string:
        return None

    string = bytearray.fromhex(hex_string).decode()
    tuple = string.split("|")
    return Page(list_hash=tuple[0], element=tuple[1])
