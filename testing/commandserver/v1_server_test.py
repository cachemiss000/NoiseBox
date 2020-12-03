import json
import unittest
from unittest.mock import Mock

from common import flags
from parameterized import parameterized
from commandserver import command_types_v1 as c_types
from commandserver import v1_server as server
from medialogic import controller, media_library

# We can do this because it's a test file, so we know it's top-level :P
FLAGS = flags.FLAGS
FLAGS.init()


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


class CommandParsingTest(unittest.TestCase):
    def setUp(self):
        FLAGS.override_flag("debug", True)


    def test_parameterless_not_empty(self):
        """Sanity test to ensure the next test isn't running on the empty set."""
        self.assertGreater(len(server.PARAMETERLESS_COMMANDS), 1,
                           "Parameterless commands '%s' should not be empty" % (server.PARAMETERLESS_COMMANDS,))

    @parameterized.expand(server.PARAMETERLESS_COMMANDS)
    def test_parse_empty_commands(self, command_cls: str):
        command = {
            "command_name": command_cls
        }

        output_command = server.MediaServer.parse_command(json.dumps(command))

        self.assertTrue(isinstance(output_command, c_types.Command))
        self.assertEqual(output_command.command_name, command_cls)
        self.assertIsNone(output_command.payload)

    def test_throws_no_command_set(self):
        command = {
            "payload": {
                "play_state": True
            }
        }

        with self.assertRaises(server.ErrorResponse) as ex:
            server.MediaServer.parse_command(json.dumps(command))
        exception = ex.exception
        self.assertRegex(exception.error_message, "Command name must be specified.*")
        self.assertEqual(exception.command_status, c_types.CommandStatus.CLIENT_ERROR)

    def test_command_not_defined(self):
        command = {
            "command_name": "florbus",
            "payload": {}
        }

        with self.assertRaises(server.ErrorResponse) as ex:
            server.MediaServer.parse_command(json.dumps(command))
        exception = ex.exception
        self.assertRegex(exception.error_message,
                         "Command name 'florbus' is not a valid %s command" % (server.VERSION,))
        self.assertEqual(exception.command_status, c_types.CommandStatus.CLIENT_ERROR)


def is_successful_response(response: c_types.Response):
    if response.command_status in c_types.CommandStatus.SUCCESS_TYPES:
        return True

    if isinstance(response.error_data, Exception):
        raise AssertionError(
            "Received error response from server: '%s'" % (response.error_message,)) from response.error_data

    else:
        raise AssertionError("Received error response from server: '%s'" % (response.error_message,))


class PlayCommandTest(unittest.TestCase):
    def setUp(self):
        FLAGS.override_flag("debug", True)

    @parameterized.expand([(True,), (False,)])
    def test_play_no_arg_toggles(self, starting_play_state):
        """Check to make sure playing_state is toggled."""
        command = {"command_name": c_types.TogglePlayCommand.COMMAND_NAME}
        server, c, ml = mock_server()
        c.playing_state = starting_play_state
        response = c_types.TogglePlayResponse.from_json(server.accept(json.dumps(command)))
        self.assertTrue(is_successful_response(response))
        self.assertIsNone(response.error_message)
        self.assertIsNone(response.error_data)

        # We use "assertEqual(..., not <expression)" instead of "assertNotEqual(....)"
        # because != will return true when comparing an object to a boolean, but
        # <object> == not <boolean> will always return false (among other reasons).
        #
        # IoW: This ensures we don't miss bad return types.
        self.assertEqual(response.new_play_state, not starting_play_state)
        self.assertEqual(c.playing(), not starting_play_state)

    @parameterized.expand([(True,), (False,)])
    def test_playing_true_false_works(self, new_play_state):
        """Check to make sure play_state is respected."""
        command = {
            "command_name": c_types.TogglePlayCommand.COMMAND_NAME,
            "payload": {
                "play_state": new_play_state
            }
        }
        server, c, ml = mock_server()
        c.playing_state = not new_play_state
        response = c_types.TogglePlayResponse.from_json(server.accept(json.dumps(command)))
        self.assertTrue(is_successful_response(response))
        self.assertIsNone(response.error_message)
        self.assertIsNone(response.error_data)
        self.assertEqual(response.new_play_state, new_play_state)
        self.assertEqual(c.playing(), new_play_state)

    @parameterized.expand([(True,), (False,)])
    def test_set_playing_idempotent(self, new_play_state):
        """Checks to make sure the server actually sets the playing state when called."""
        command = {
            "command_name": c_types.TogglePlayCommand.COMMAND_NAME,
            "payload": {
                "play_state": new_play_state,
            }
        }
        server, c, ml = mock_server()
        c.playing_state = new_play_state
        response = c_types.TogglePlayResponse.from_json(server.accept(json.dumps(command)))
        self.assertTrue(is_successful_response(response))
        self.assertEqual(response.new_play_state, new_play_state)
        self.assertEqual(c.playing(), new_play_state)

    # Define a quick, hacky enum to make parameterized code more readable.
    # Use strings instead of the traditional ints to make parameterized test names easier to read.
    USE_TOGGLE = "UseToggle"
    USE_EXPLICIT_SET = "UseExplicitSet"

    @parameterized.expand([(USE_TOGGLE,), (USE_EXPLICIT_SET,)])
    def test_setting_play_thorws_exception(self, command_type):
        command = {"command_name": c_types.TogglePlayCommand.COMMAND_NAME}

        if command_type == PlayCommandTest.USE_TOGGLE:
            command["payload"] = {"play_state": True}
        else:
            assert command_type == PlayCommandTest.USE_EXPLICIT_SET

        server, c, ml = mock_server()
        ex = Exception("TestyMcTestface")

        def throw_ex(unused_self=None, arg=None):
            raise ex

        c.set_pause = c.toggle_pause = throw_ex

        response = c_types.Response.from_json(server.accept(json.dumps(command)))
        self.assertRegex(response.error_message, "Unexpected error.*")
        self.assertEqual(response.error_data, str(ex))

    @parameterized.expand([(USE_TOGGLE,), (USE_EXPLICIT_SET,)])
    def test_exception_data_thrown_on_debug(self, command_type):
        """Test to ensure debug=False flag causes no internal error data to get attached to the response.

        Uses FLAGS.override_flag. By default, "debug" is set to true (see top of this file).
        """
        command = {"command_name": c_types.TogglePlayCommand.COMMAND_NAME}

        if command_type == PlayCommandTest.USE_TOGGLE:
            command["payload"] = {"play_state": True}
        else:
            assert command_type == PlayCommandTest.USE_EXPLICIT_SET

        server, c, ml = mock_server()

        def throw_ex(unused_self, arg=None):
            raise Exception("TestyMcTestface")

        with FLAGS.override_flag("debug", False):
            c.set_pause = c.toggle_pause = throw_ex
            response = c_types.TogglePlayResponse.from_json(server.accept(json.dumps(command)))

        self.assertRegex(response.error_message, "Unexpected error.*")
        self.assertEqual(response.error_data, None)


if __name__ == '__main__':
    unittest.main()
