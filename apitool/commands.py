import argparse

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

