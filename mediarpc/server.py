import mediarpc.media_server_pb2 as ms_pb
import mediarpc.media_server_pb2_grpc as ms_pb_grpc
from medialogic import media_library, controller
import grpc


class MediaServer(ms_pb_grpc.MediaControlService):
    def __init__(self, controller: controller.Controller, media_library: media_library.MediaLibrary):
        super(MediaServer, self).__init__()
        self.media_library = media_library
        self.controller = controller

    def Play(self, play_request, context) -> ms_pb.PlayResponse:
        self.controller.resume()
        return ms_pb.PlayResponse()

    def add_to_server(self, server: grpc.Server):
        ms_pb_grpc.add_MediaControlServiceServicer_to_server(self, server)
