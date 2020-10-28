import collections
from typing import List, Tuple

import mediarpc.media_server_pb2 as ms_pb
import mediarpc.media_server_pb2_grpc as ms_pb_grpc
from medialogic import media_library, controller
import grpc

DEFAULT_MAX_RESPONSE_SIZE = 200

# TODO: For type sanity, this NEEDS to be a class. Goddamn.
Page = collections.namedtuple("Page", ["list_hash", "element"])


class OutdatedPageException(Exception):
    pass


class MediaServer(ms_pb_grpc.MediaControlService):
    def __init__(self, controller: controller.Controller, media_library: media_library.MediaLibrary):
        super(MediaServer, self).__init__()
        self.media_library = media_library
        self.controller = controller

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
