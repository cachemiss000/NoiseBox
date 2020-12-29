import websockets

from commandserver.server_types.v1_command_types import TogglePlayCommand, Message, ListPlaylistsCommand, \
    ListPlaylistsEvent, prettify_message
from common import command
from common.safe_arg_parse import SafeArgumentParser


class PlayCommand(command.Command):
    """
    Send a command to the API to begin playing music.
    """

    def __init__(self, websockets_client: websockets.WebSocketClientProtocol):
        ap = SafeArgumentParser(description="Begin playing audio")
        super(PlayCommand, self).__init__("play", ap)
        self.ws_client = websockets_client

    async def do_function(self, **arg_dict):
        await self.ws_client.send(TogglePlayCommand.create().wrap().json())
        print("Response:\n%s" % (prettify_message(await self.ws_client.recv()),))


class ListPlaylists(command.Command):
    """
    Send a command to the API to list all the playlists
    """

    def __init__(self, websockets_client: websockets.WebSocketClientProtocol):
        ap = SafeArgumentParser(description="List playlists")
        super(ListPlaylists, self).__init__("listplaylists", ap)
        self.ws_client = websockets_client

    async def do_function(self, **arg_dict):
        await self.ws_client.send(ListPlaylistsCommand.create().wrap().json())
        response = Message.parse_raw(await self.ws_client.recv())
        if response.get_error():
            print("Received error:")
            print(prettify_message(response.get_error()))
            return

        print("Playlists:\n%s" % (response.unwrap(ListPlaylistsEvent).playlists,))
