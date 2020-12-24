import json
import unittest
from unittest.mock import Mock

from absl import flags
from absl.testing import absltest
from parameterized import parameterized

from commandserver import v1_server as server
from commandserver.server_types import v1_command_types as c_types
from commandserver.server_types.v1_command_types import Event
from common import test_utils
from common.test_utils import FlagsTest, MockClient
from medialogic import controller, media_library

FLAGS = flags.FLAGS


class MockController(Mock):
    def __init__(self):
        super(MockController, self).__init__(spec=controller.Controller)
        self.playing_state = False

    def set_pause(self, pause_state):
        self.playing_state = not pause_state
        return not self.playing_state

    def toggle_pause(self):
        self.playing_state = not self.playing_state

    def playing(self):
        return self.playing_state

    def paused(self):
        return not self.playing_state


def mock_server() -> (server.MediaServer, controller.Controller, media_library.MediaLibrary):
    c = MockController()
    ml = Mock()
    media_server = server.MediaServer(c, ml)

    return media_server, c, ml


class CommandParsingTest(FlagsTest, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super(CommandParsingTest, self).setUp()
        FLAGS.debug = True

    def test_parameterless_not_empty(self):
        """Sanity test to ensure the next test isn't running on the empty set."""
        self.assertGreater(len(server.PARAMETERLESS_COMMANDS), 1,
                           "Parameterless commands '%s' should not be empty" % (server.PARAMETERLESS_COMMANDS,))

    @parameterized.expand(server.PARAMETERLESS_COMMANDS)
    def test_parse_empty_commands(self, command_cls: str):
        command = {
            "message_name": command_cls
        }

        output_command = server.MediaServer.parse_command(json.dumps(command))

        self.assertTrue(isinstance(output_command, c_types.Command))
        self.assertEqual(output_command.message_name, command_cls)
        self.assertIsNone(output_command.payload)

    def test_throws_no_command_set(self):
        command = {
            "payload": {
                "play_state": True
            }
        }

        with self.assertRaises(c_types.ErrorEvent) as ex:
            server.MediaServer.parse_command(json.dumps(command))
        exception = ex.exception
        self.assertRegex(exception.error_message, "Command name must be specified.*")
        self.assertEqual(exception.error_type, c_types.ErrorType.CLIENT_ERROR)

    async def test_command_not_defined(self):
        command = {
            "message_name": "florbus",
            "payload": {}
        }

        mc = MockClient()
        media_server = server.MediaServer(Mock(), Mock())
        await media_server.accept(json.dumps(command), mc)

        self.assertRegex(mc.get_error().error_message,
                         "Command name 'florbus' is not a valid %s command" % (server.VERSION,))


class PlayCommandTest(FlagsTest, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super(PlayCommandTest, self).setUp()
        FLAGS.debug = True

    @parameterized.expand([(True,), (False,)])
    async def test_play_no_arg_toggles(self, starting_play_state):
        """Check to make sure playing_state is toggled."""
        server, c, ml = mock_server()
        c.playing_state = starting_play_state
        command = {"message_name": c_types.TogglePlayCommand.MESSAGE_NAME}
        expected_response = Event(message_name=c_types.PlayStateEvent.MESSAGE_NAME,
                                  payload=c_types.PlayStateEvent(not c.playing_state))
        client = MockClient(Mock())
        await server.accept(json.dumps(command), client)
        self.assertEqual(client.sent_messages, [expected_response])

        # We use "assertEqual(..., not <expression)" instead of "assertNotEqual(....)"
        # because != will return true when comparing an object to a boolean, but
        # <object> == not <boolean> will always return false (among other reasons).
        #
        # IoW: This ensures we don't miss bad return types.
        self.assertEqual(c.playing(), not starting_play_state)

    @parameterized.expand([(True,), (False,)])
    async def test_playing_true_false_works(self, new_play_state):
        """Check to make sure play_state is respected."""
        command = {
            "message_name": c_types.TogglePlayCommand.MESSAGE_NAME,
            "payload": {
                "play_state": new_play_state
            }
        }
        server, c, ml = mock_server()
        c.playing_state = not new_play_state
        mc = MockClient()
        await server.accept(json.dumps(command), mc)

        self.assertEqual(mc.get_only_message().unwrap(c_types.PlayStateEvent).new_play_state, new_play_state)
        self.assertEqual(c.playing(), new_play_state)

    @parameterized.expand([(True,), (False,)])
    async def test_set_playing_idempotent(self, new_play_state):
        """Checks to make sure the server actually sets the playing state when called."""
        command = {
            "message_name": c_types.TogglePlayCommand.MESSAGE_NAME,
            "payload": {
                "play_state": new_play_state,
            }
        }
        server, c, ml = mock_server()
        c.playing_state = new_play_state
        mc = MockClient()
        await server.accept(json.dumps(command), mc)

        self.assertEqual(mc.get_only_message().unwrap(c_types.PlayStateEvent).new_play_state, new_play_state)
        self.assertEqual(c.playing(), new_play_state)

    # Define a quick, hacky enum to make parameterized code more readable.
    # Use strings instead of the traditional ints to make parameterized test names easier to read.

    # Toggle between "play_state" implicitly, e.g. without setting "TogglePlayCommand.play_state"
    USE_TOGGLE = "UseToggle"

    # Explicitly set "play_state", e.g. "TogglePlayCommand().play_state = True"
    USE_EXPLICIT_SET = "UseExplicitSet"

    @parameterized.expand([(USE_TOGGLE,), (USE_EXPLICIT_SET,)])
    async def test_setting_play_thorws_exception(self, command_type):
        command = {"message_name": c_types.TogglePlayCommand.MESSAGE_NAME}

        if command_type == PlayCommandTest.USE_EXPLICIT_SET:
            command["payload"] = {"play_state": True}
        else:
            assert command_type == PlayCommandTest.USE_TOGGLE

        server, c, ml = mock_server()
        ex = Exception("TestyMcTestface")

        def throw_ex(unused_self=None, arg=None):
            raise ex

        c.set_pause = c.toggle_pause = throw_ex

        mc = MockClient()
        await server.accept(json.dumps(command), mc)
        self.assertRegex(mc.get_error().error_message, "Unexpected error.*")
        self.assertEqual(mc.get_error().error_data, str(ex))

    @parameterized.expand([(USE_TOGGLE,), (USE_EXPLICIT_SET,)])
    async def test_exception_data_thrown_on_debug(self, command_type):
        """Test to ensure debug=False flag causes no internal error data to get attached to the response.

        Uses FLAGS.override_flag. By default, "debug" is set to true (see top of this file).
        """
        command = {"message_name": c_types.TogglePlayCommand.MESSAGE_NAME}

        if command_type == PlayCommandTest.USE_TOGGLE:
            command["payload"] = {"play_state": True}
        else:
            assert command_type == PlayCommandTest.USE_EXPLICIT_SET

        server, c, ml = mock_server()
        mc = MockClient(Mock())

        def throw_ex(unused_self, arg=None):
            raise Exception("TestyMcTestface")

        with test_utils.override_flag("debug", False):
            c.set_pause = c.toggle_pause = throw_ex
            await server.accept(json.dumps(command), mc)

        response = mc.get_error()
        self.assertRegex(response.error_message, "Unexpected error.*")
        self.assertEqual(response.error_data, None)


if __name__ == '__main__':
    absltest.main()
