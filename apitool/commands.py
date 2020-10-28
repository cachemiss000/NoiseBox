from common import command
from common.safe_arg_parse import SafeArgumentParser
from mediarpc import media_server_pb2_grpc as ms_pb_grpc
from mediarpc import media_server_pb2 as ms_pb


class PlayCommand(command.Command):
    """
    Send a command to the API to begin playing music.
    """

    def __init__(self, mediarpc_stub: ms_pb_grpc.MediaControlServiceStub):
        ap = SafeArgumentParser(description="Begin playing audio")
        super(PlayCommand, self).__init__("play", ap)
        self.stub = mediarpc_stub

    def do_function(self, **arg_dict):
        self.stub.Play(ms_pb.PlayRequest())


class ListPlaylists(command.Command):
    """
    Send a command to the API to list all the playlists
    """

    def __init__(self, mediarpc_stub: ms_pb_grpc.MediaControlServiceStub):
        ap = SafeArgumentParser(description="List playlists")
        super(ListPlaylists, self).__init__("listplaylists", ap)
        self.stub = mediarpc_stub

    def do_function(self, **arg_dict):
        itr_count = 0
        response = ms_pb.ListPlaylistsResponse()
        names = []
        while itr_count <= 0 or (itr_count < 10 and response.next_page_token):
            itr_count += 1
            request = ms_pb.ListPlaylistsRequest(page_token=response.next_page_token, max_num_entries=3)
            response = self.stub.ListPlaylists(request)
            names.extend(response.playlist_names)
        print("Playlists: {\n%s\n}" % (names,))
