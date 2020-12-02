import json
import unittest

from parameterized import parameterized
from commandserver import command_types_v1 as c_types
from commandserver.v1_server import MediaServer


class CommandParsingTest(unittest.TestCase):

    def test_parameterless_not_empty(self):
        """Sanity test to ensure the next test isn't running on the empty set."""
        self.assertGreater(len(c_types.PARAMETERLESS_COMMANDS), 1,
                           "Parameterless commands '%s' should not be empty" % (c_types.PARAMETERLESS_COMMANDS,))

    @parameterized.expand(c_types.PARAMETERLESS_COMMANDS)
    def test_parse_empty_commands(self, command_cls: c_types.CommandCls):
        command = {
            "command_name": command_cls.COMMAND_NAME
        }

        output_command = MediaServer.parse_command(json.dumps(command))

        self.assertTrue(isinstance((output_command, c_types.Command)))
        self.assertEqual(output_command.command_name, command_cls.COMMAND_NAME)
        self.assertIsNone(output_command.payload)

if __name__ == '__main__':
    unittest.main()
