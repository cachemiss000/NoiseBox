import json
import unittest
from unittest.mock import Mock

from absl import flags
from absl.testing import absltest
from parameterized import parameterized

from commandserver import v1_server as server
from commandserver.server_types import v1_command_types as c_types
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

    async def test_event_not_defined(self):
        message = {
            "event": {
                "event_name": "florbus",
            }
        }

        mc = MockClient()
        media_server = server.MediaServer(Mock(), Mock())
        await media_server.accept(json.dumps(message), mc)

        self.assertRegex(mc.get_error().error_message,
                         "Could not find event name 'florbus' in possible event names:")

    async def test_command_not_defined(self):
        message = {
            "command": {
                "command_name": "florbus",
            }
        }

        mc = MockClient()
        media_server = server.MediaServer(Mock(), Mock())
        await media_server.accept(json.dumps(message), mc)

        self.assertRegex(mc.get_error().error_message,
                         "Could not find command name 'florbus' in possible command names:")


class PlayCommandTest(FlagsTest, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super(PlayCommandTest, self).setUp()
        FLAGS.debug = True

    @parameterized.expand([(True,), (False,)])
    async def test_play_no_arg_toggles(self, starting_play_state):
        """Check to make sure playing_state is toggled."""
        this_server, c, ml = mock_server()
        c.playing_state = starting_play_state
        command_msg = c_types.TogglePlayCommand.create().wrap()
        expected_response = c_types.PlayStateEvent.create(
            new_play_state=not c.playing_state).wrap()
        client = MockClient(Mock())
        await this_server.accept(command_msg.json(), client)
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
        command_msg = c_types.TogglePlayCommand.create(play_state=new_play_state).wrap()
        this_server, c, ml = mock_server()
        c.playing_state = not new_play_state
        mc = MockClient()
        await this_server.accept(command_msg.json(), mc)

        self.assertEqual(mc.get_only_message().unwrap(c_types.PlayStateEvent).new_play_state, new_play_state)
        self.assertEqual(c.playing(), new_play_state)

    @parameterized.expand([(True,), (False,)])
    async def test_set_playing_idempotent(self, new_play_state):
        """Checks to make sure the server actually sets the playing state when called."""
        command_msg = c_types.TogglePlayCommand.create(play_state=new_play_state).wrap()
        this_server, c, ml = mock_server()
        c.playing_state = new_play_state
        mc = MockClient()
        await this_server.accept(command_msg.json(), mc)

        self.assertEqual(mc.get_only_message().unwrap(c_types.PlayStateEvent).new_play_state, new_play_state)
        self.assertEqual(c.playing(), new_play_state)

    # Define a quick, hacky enum to make parameterized code more readable.
    # Use strings instead of the traditional ints to make parameterized test names easier to read.

    # Toggle between "play_state" implicitly, e.g. without setting "TogglePlayCommand.play_state"
    USE_TOGGLE = "UseToggle"

    # Explicitly set "play_state", e.g. "TogglePlayCommand().play_state = True"
    USE_EXPLICIT_SET = "UseExplicitSet"

    @parameterized.expand([(USE_TOGGLE,), (USE_EXPLICIT_SET,)])
    async def test_setting_play_throws_exception(self, command_type):
        command = c_types.TogglePlayCommand.create()

        if command_type == PlayCommandTest.USE_EXPLICIT_SET:
            command.play_state = True
        else:
            assert command_type == PlayCommandTest.USE_TOGGLE
        command_msg = command.wrap()

        this_server, c, ml = mock_server()
        ex = Exception("TestyMcTestFace")

        def throw_ex(_unused_self=None, _arg=None):
            raise ex

        c.set_pause = c.toggle_pause = throw_ex

        mc = MockClient()
        await this_server.accept(command_msg.json(), mc)
        self.assertRegex(mc.get_error().error_message, "Unexpected error.*")
        self.assertEqual(mc.get_error().error_data, str(ex))

    @parameterized.expand([(USE_TOGGLE,), (USE_EXPLICIT_SET,)])
    async def test_exception_data_thrown_on_debug(self, command_type):
        """Test to ensure debug=False flag causes no internal error data to get attached to the response.

        Uses FLAGS.override_flag. By default, "debug" is set to true (see top of this file).
        """
        command = {"command_name": c_types.TogglePlayCommand.COMMAND_NAME}

        if command_type == PlayCommandTest.USE_TOGGLE:
            command["payload"] = {"play_state": True}
        else:
            assert command_type == PlayCommandTest.USE_EXPLICIT_SET

        this_server, c, ml = mock_server()
        mc = MockClient(Mock())

        def throw_ex(_unused_self, _arg=None):
            raise Exception("TestyMcTestFace")

        with test_utils.override_flag("debug", False):
            c.set_pause = c.toggle_pause = throw_ex
            await this_server.accept(json.dumps(command), mc)

        response = mc.get_error()
        self.assertRegex(response.error_message, "Message failed validation.*")
        self.assertEqual(response.error_data, None)


if __name__ == '__main__':
    absltest.main()
