import asyncio
import logging
import tracemalloc
import unittest
from typing import List

import websockets
from absl.testing import absltest

from commandserver import websocket_muxer, server_codes, server_exceptions
from commandserver.server_types import v1_command_types as c_types
from commandserver.server_types.v1_command_types import Message
from common.test_utils import FlagsTest

CLOSE_MESSAGE = "close sesame"

tracemalloc.start(1000)


class TestServer(websocket_muxer.Server):

    def __init__(self, expect_list: List[c_types.Message], response_list: List[c_types.Message],
                 close_message: str = CLOSE_MESSAGE):
        self.expect_list = expect_list
        self.response_list = response_list
        self.close_message = close_message

    async def accept(self, message: str, client: websocket_muxer.ClientSession) -> None:
        if message == self.close_message:
            raise server_exceptions.CloseConnectionException

        expected = self.expect_list.pop(0)
        if Message.parse_raw(message) != expected:
            raise server_exceptions.ClientError("expected '%s' got '%s'" % (expected, message))
        await client.send(self.response_list.pop(0))


async def send_commands(ws: websockets.WebSocketClientProtocol, messages: List[c_types.MessageObj],
                        close_message: str = CLOSE_MESSAGE):
    try:
        for message in messages:
            await ws.send(message.wrap().json())
        await ws.send(close_message)
    except websockets.ConnectionClosedError as e:
        logging.exception("Connection closed early: %s" % (e,))


def events_from(*argv) -> List[c_types.Event]:
    return [event_from(arg) for arg in argv]


def event_from(song_name: str) -> c_types.Event:
    return c_types.SongPlayingEvent.create(current_song=c_types.Song(name=song_name))


def commands_from(*argv: bool) -> List[c_types.Command]:
    return [command_from(arg) for arg in argv]


def command_from(arg: bool) -> c_types.Command:
    return c_types.TogglePlayCommand.create(play_state=arg)


def expected_messages(messages: List[c_types.Message]) -> List[c_types.Event]:
    return [message.unwrap(c_types.SongPlayingEvent) for message in messages]


def wrap_all(*argv: c_types.MessageObj) -> List[c_types.Message]:
    return list(arg.wrap() for arg in argv)


class ResponseCollector:

    def __init__(self):
        self.responses: List[c_types.Message] = []

    async def route_responses(self, ws: websockets.WebSocketClientProtocol):
        async for message in ws:
            self.responses.append(c_types.Message.parse_raw(message).event)


class WebsocketContextManager:
    """Quick and dirty context manager.

    Clients call "connect" to get new client websocket connections, and call "serve" to get new server connections.

    All connections are context-managed, and will be closed at the end of a test as long as the caller calls
    inside a "with" statement.
    """

    def __init__(self):
        self.websocket_clients = []
        self.websocket_servers = []

    async def connect(self, *argv, **kwargs):
        ws = await websockets.connect(*argv, **kwargs)
        self.websocket_clients.append(ws)
        return ws

    async def serve(self, *argv, **kwargs):
        ws = await websockets.serve(*argv, **kwargs)
        self.websocket_servers.append(ws)
        return ws

    async def __aenter__(self):
        return self

    async def __aexit__(self, unused_1, unused_2, unused_3):
        for ws in self.websocket_clients:
            await ws.close()
        for ws in self.websocket_servers:
            ws.close()
            await ws.wait_closed()


class WebsocketMuxerTest(FlagsTest, unittest.IsolatedAsyncioTestCase):

    def assertConnectionClosedSuccessfully(self, client):
        self.assertEqual(client.close_code, 1000,
                         "Client did not close successfully.\n"
                         "For close code 4006, check the top of the logs.\n"
                         "  - code=%s\n"
                         "  - reason=%s" % (
                             client.close_code, client.close_reason))

    async def test_websocket_startup_and_bad_uri(self):
        muxer = websocket_muxer.WebsocketMuxer()
        async with WebsocketContextManager() as ws_ctx:
            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)

            client = await ws_ctx.connect("ws://localhost:8765/florgus")

        self.assertEqual(client.close_code, server_codes.UNSUPPORTED_URI)
        self.assertRegex(client.close_reason, "path '.*florgus.*' not found")

    async def test_websocket_returns_response(self):
        muxer = websocket_muxer.WebsocketMuxer()
        client_commands = commands_from(True, False, True)
        server_responses = events_from("blorgus1", "blorgus2", "blorgus3")
        test_server = TestServer(expect_list=wrap_all(*client_commands),
                                 response_list=wrap_all(*server_responses))
        rc = ResponseCollector()

        async with WebsocketContextManager() as ws_ctx:
            muxer.register("/florgus", test_server)
            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)
            client = await ws_ctx.connect("ws://localhost:8765/florgus")

            collection_cr = rc.route_responses(client)
            commands_cr = send_commands(client, client_commands)

            await asyncio.gather(collection_cr, commands_cr)

        self.assertConnectionClosedSuccessfully(client)
        self.assertListEqual(rc.responses, server_responses)

    async def test_multiple_paths(self):
        muxer = websocket_muxer.WebsocketMuxer()

        client_commands_1 = commands_from(True, False)
        server_responses_1 = events_from("blorgus1", "blorgus2")
        test_server_1 = TestServer(expect_list=wrap_all(*client_commands_1),
                                   response_list=wrap_all(*server_responses_1))
        muxer.register("/test1", test_server_1)
        rc1 = ResponseCollector()

        client_commands_2 = commands_from(True)
        server_responses_2 = events_from("blorgus2")
        test_server_2 = TestServer(expect_list=wrap_all(*client_commands_2),
                                   response_list=wrap_all(*server_responses_2))
        muxer.register("/test2", test_server_2)
        rc2 = ResponseCollector()

        async with WebsocketContextManager() as ws_ctx:
            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)

            client_1 = await ws_ctx.connect("ws://localhost:8765/test1")
            client_2 = await ws_ctx.connect("ws://localhost:8765/test2")
            commands_1_cr = send_commands(client_1, client_commands_1)
            responses_1_cr = rc1.route_responses(client_1)
            commands_2_cr = send_commands(client_2, client_commands_2)
            responses_2_cr = rc2.route_responses(client_2)

            await asyncio.gather(commands_1_cr, responses_1_cr, commands_2_cr, responses_2_cr)

        self.assertConnectionClosedSuccessfully(client_1)
        self.assertConnectionClosedSuccessfully(client_2)

        self.assertEqual(rc1.responses, expected_messages(wrap_all(*server_responses_1)))
        self.assertEqual(rc2.responses, expected_messages(wrap_all(*server_responses_2)))

    async def test_server_error(self):
        muxer = websocket_muxer.WebsocketMuxer()
        exception = server_exceptions.ClientError("test error")

        class ExceptionHandler(websocket_muxer.Server):
            async def accept(self, message: str, _client: websocket_muxer.ClientSession) -> None:
                raise exception

        muxer.register("/exception_test", ExceptionHandler())

        async with WebsocketContextManager() as ws_ctx:
            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)
            client = await ws_ctx.connect("ws://localhost:8765/exception_test")
            await client.send("literally anything")
            with self.assertRaises(websockets.ConnectionClosedError):
                await client.send("anything else")
                await client.recv()  # Force it to close out.

        self.assertEqual(client.close_code, server_codes.BAD_CLIENT)
        self.assertRegex(client.close_reason, ".*%s.*" % (str(exception),))


if __name__ == '__main__':
    absltest.main()
