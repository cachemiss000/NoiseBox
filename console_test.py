"""Tests for console.py"""

import unittest

from console import ConsoleOutput, Command, Console
from console import Console


class ConsoleTest(unittest.TestCase):
    def test_write_parsed_correctly(self):
        console = Console()
        c_out = console.console_output
        console.readline_output.put("test 'this is a test' 'and another test'\n")
        console.process_readline(c_out)
        console.close()
        commands = list(c_out.commands(timeout=1.5))
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0], Command(command="test", arguments=["this is a test", "and another test"]))

    def test_write_multiple_commands(self):
        console = Console()
        c_out = console.console_output
        console.readline_output.put("test1 'something'")
        console.readline_output.put("test2 'something else'")
        console.readline_output.put("test3 'something yet more'\n")
        console.process_readline(c_out)
        console.close()

        commands = list(c_out.commands(timeout=1.5))

        self.assertListEqual(commands, [
            Command("test1", ["something"]),
            Command("test2", ["something else"]),
            Command("test3", ["something yet more"])
        ])

    def test_newline_only(self):
        console = Console()
        c_out = console.console_output
        console.readline_output.put("\n")
        console.process_readline(c_out)
        console.close()

        commands = list(c_out.commands(timeout=1.5))

        self.assertListEqual(commands, [])


if __name__ == '__main__':
    unittest.main()
