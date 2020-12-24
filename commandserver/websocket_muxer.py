import logging
import re
from typing import Protocol, Dict, Union

import websockets
from absl import flags

# Import server flags.
# noinspection PyUnresolvedReferences
import commandserver.server_flags
from commandserver import server_codes, server_exceptions
from common import print_controller
from messages.message_map import Message, MessageCls

FLAGS = flags.FLAGS


class ClientSession:
    def __init__(self, ws: websockets.WebSocketServerProtocol):
        self._ws = ws

    async def send(self, message: Union[Message, MessageCls]):
        await self._ws.send(message.wrap().to_json())


class Server(Protocol):

    async def accept(self, message: str, client: ClientSession) -> None:
        """Accept a frame from the client.

        Cannot block. If you need blocking, log a task in a local datastore quickly and return a handle to it, then
        return the status on subsequent queries from the client.
        """
        pass


class WebsocketMuxer:
    """A muxer which handles the websocket-y ness, and redirects messages to servers as appropriate.

    Currently we only have 1 server hosted at /noisebox/command_server/v1, so a more thorough solution isn't
    implemented.
    """

    def __init__(self):
        self.servers: Dict[str, Server] = {}
        self.logger = print_controller.logging_printer('websocket_mux',
                                                       min_error_level_to_print=
                                                       logging.getLevelName(FLAGS.server_log_level))

    URL_REGEX: re.Pattern = re.compile(r'^/?\w*(/\w*)*/?$')

    def register(self, path: str, server: Server):
        if not isinstance(path, str):
            raise ValueError("expected string for path, got '%s'" % (path,))
        if not WebsocketMuxer.URL_REGEX.match(path):
            raise ValueError("input path '%s' does not match expected regex '%s'" % (path, WebsocketMuxer.URL_REGEX))
        if path in self.servers:
            self.logger.warn("path '%s' already registered on muxer to server '%s'" % (path, self.servers.get(path)))

        self.servers[path] = server

    async def handle_session(self, ws: websockets.WebSocketServerProtocol, path: str):
        server = self.servers.get(path)
        if not server:
            self.logger.debug("user attempted to connect to path '%s', which doesn't exist" % (path,))
            await ws.close(server_codes.UNSUPPORTED_URI, "path '%s' not found" % (path,))
            return

        await ws.ensure_open()
        session = ClientSession(ws)
        async for message in ws:
            try:
                if isinstance(message, bytes):
                    raise server_exceptions.ClientError("this server does not accept binary frames")
                await server.accept(message, session)
            except server_exceptions.CloseConnectionException as e:
                self.logger.debug("client @ '%s' asked to close the server" % (path,))
                await ws.close()
                return
            except server_exceptions.ClientError as e:
                self.logger.warn("client @ '%s' misbehaved: '%s', closing the connection" % (path, e))
                await ws.close(server_codes.BAD_CLIENT, str(e))
                return

        self.logger.debug("server loop finished for connection path '%s'" % (path,))
        await ws.wait_closed()
        self.logger.debug("server @ '%s' closed. Code: '%s', Reason: '%s'" % (path, ws.close_code, ws.close_reason))
