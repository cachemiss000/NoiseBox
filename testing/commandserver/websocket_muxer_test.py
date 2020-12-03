import asyncio
import logging
import unittest
from typing import List, Callable, Protocol
from unittest import mock

import websockets
import tracemalloc

from commandserver import websocket_muxer, server_codes, server_exceptions
from common import flags

CLOSE_MESSAGE = "close sesame"

FLAGS = flags.FLAGS
FLAGS.init()
tracemalloc.start(1000)


class TestServer(websocket_muxer.Server):

    def __init__(self, expect_list: List[str], response_list: List[str], close_message: str = CLOSE_MESSAGE):
        self.expect_list = expect_list
        self.response_list = response_list
        self.close_message = close_message

    def accept(self, message: str):
        if message == self.close_message:
            raise server_exceptions.CloseConnectionException

        expected = self.expect_list.pop(0)
        if message != expected:
            raise server_exceptions.ClientError("expected '%s' got '%s'" % (expected, message))
        return self.response_list.pop(0)


async def send_commands(ws: websockets.WebSocketClientProtocol, messages: List[str],
                        close_message: str = CLOSE_MESSAGE) -> List[str]:
    response = []
    try:
        for message in messages:
            await ws.send(message)
            response.append(await ws.recv())
        await ws.send(close_message)
    except websockets.ConnectionClosedError as e:
        logging.exception("Connection closed early")
        return response
    return response


class WebsocketContextManager:

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


class WebsocketMuxerTest(unittest.IsolatedAsyncioTestCase):

    def assertConnectionClosedSuccessfully(self, client):
        self.assertEqual(client.close_code, 1000,
                         "Client did not close successfully.\n"
                         "For close code 4006, check the top of the logs.\n"
                         "  - code=%s\n"
                         "  - reason=%s" % (
                             client.close_code, client.close_reason))

    async def test_websocket_startup_and_bad_uri(self):
        async with WebsocketContextManager() as ws_ctx:
            muxer = websocket_muxer.WebsocketMuxer()
            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)

            client = await ws_ctx.connect("ws://localhost:8765/florgus")

        self.assertEqual(client.close_code, server_codes.UNSUPPORTED_URI)
        self.assertRegex(client.close_reason, "path '.*florgus.*' not found")

    async def test_websocket_returns_response(self):
        async with WebsocketContextManager() as ws_ctx:
            muxer = websocket_muxer.WebsocketMuxer()
            client_commands = ["florgus1", "florgus2", "florgus3"]
            server_responses = ["blorgus1", "blorgus2", "blorgus3"]

            test_server = TestServer(expect_list=list(client_commands),
                                     response_list=list(server_responses))
            muxer.register("/florgus", test_server)

            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)

            client = await ws_ctx.connect("ws://localhost:8765/florgus")
            responses = await send_commands(client, client_commands)

        self.assertConnectionClosedSuccessfully(client)
        self.assertListEqual(responses, server_responses)

    async def test_multiple_paths(self):
        async with WebsocketContextManager() as ws_ctx:
            muxer = websocket_muxer.WebsocketMuxer()
            client_commands_1 = ["florgus1"]
            client_commands_2 = ["florgus2"]
            server_responses_1 = ["blorgus1"]
            server_responses_2 = ["blorgus2"]

            test_server_1 = TestServer(expect_list=list(client_commands_1),
                                       response_list=list(server_responses_1))
            test_server_2 = TestServer(expect_list=list(client_commands_2),
                                       response_list=list(server_responses_2))

            muxer.register("/test1", test_server_1)
            muxer.register("/test2", test_server_2)
            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)

            client_1 = await ws_ctx.connect("ws://localhost:8765/test1")
            client_2 = await ws_ctx.connect("ws://localhost:8765/test2")
            responses_1 = await send_commands(client_1, client_commands_1)
            responses_2 = await send_commands(client_2, client_commands_2)

        self.assertConnectionClosedSuccessfully(client_1)
        self.assertConnectionClosedSuccessfully(client_2)

        self.assertEqual(responses_1, server_responses_1)
        self.assertEqual(responses_2, server_responses_2)

    async def test_server_error(self):
        async with WebsocketContextManager() as ws_ctx:
            muxer = websocket_muxer.WebsocketMuxer()
            exception = server_exceptions.ClientError("test error")

            class ExceptionHandler(websocket_muxer.Server):
                def accept(self, message: str):
                    raise exception

            muxer.register("/exception_test", ExceptionHandler())

            await ws_ctx.serve(muxer.handle_session, "localhost", 8765)
            client = await ws_ctx.connect("ws://localhost:8765/exception_test")
            await client.send("literally anything")
            with self.assertRaises(websockets.ConnectionClosedError):
                await client.send("anything else")
                await client.recv()  # Force it to close out.

        self.assertEqual(client.close_code, server_codes.BAD_CLIENT)
        self.assertRegex(client.close_reason, ".*%s.*" % (str(exception),))


if __name__ == '__main__':
    unittest.main()
