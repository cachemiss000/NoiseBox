"""Tests for console.py"""
import logging
import unittest
from typing import List
from unittest import mock

from absl.testing import absltest

from common import print_controller
from localcli.console import Command
from localcli.console import Console


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


class PrinterTest(unittest.TestCase):

    def test_logging_printer(self):
        with (PrinterTestFixtures()) as test_fixtures:
            logger = print_controller.logging_printer("foo", logging.WARN)

            logger.log(logging.DEBUG, "1", "234")
            logger.log(logging.WARN, "2", "345", "6")
            logger.log(logging.CRITICAL, "3", "456", "7")

        test_fixtures.mock_logger.log.assert_has_calls([
            mock.call(logging.DEBUG, "1", "234"),
            mock.call(logging.WARN, "2", "345", "6"),
            mock.call(logging.CRITICAL, "3", "456", "7")
        ])

        expected_printer_calls = [
            ("foo - WARNING: 2", "345", "6"),
            ("foo - CRITICAL: 3", "456", "7")]
        self.assertListEqual(test_fixtures.test_printer.messages, expected_printer_calls)

    def test_log_level_functions(self):
        with (PrinterTestFixtures()) as test_fixtures:
            logger = print_controller.logging_printer("foo", logging.WARN)

            logger.debug("test0")
            logger.info("test1")
            logger.warn("test2")
            logger.error("test3")
            logger.critical("test4")

        test_fixtures.mock_logger.log.assert_has_calls([
            mock.call(logging.DEBUG, "test0"),
            mock.call(logging.INFO, "test1"),
            mock.call(logging.WARN, "test2"),
            mock.call(logging.ERROR, "test3"),
            mock.call(logging.CRITICAL, "test4"),
        ])

    def test_log_random_number_for_error_level(self):
        with (PrinterTestFixtures()) as test_fixtures:
            logger = print_controller.logging_printer("foo", logging.WARN)
            logger.log(500, "oh boy things are bad buddy =(")

        test_fixtures.mock_logger.log.assert_called_once_with(500, "oh boy things are bad buddy =(")
        self.assertListEqual(
            test_fixtures.test_printer.messages,
            [("foo - %s: oh boy things are bad buddy =(" % (logging.getLevelName(500),),)])


class TestPrintController(print_controller.PrintController):
    def __init__(self):
        self.messages: List[any] = []

    def print(self, msg: str, *argv):
        self.messages.append((msg, *argv))


class PrinterTestFixtures:
    """Super hacky class that replaces everything we need for Printer tests with fakes and mocks.

    Use a "with(TextFixtures()) as tf:" block to encapsulate ALL printer test code (arrange & act), then
    retrieve the fakes and mocks when in the "assert" block (see CONTRIBUTIONS_README for 'arrange, act, assert'
    explanation)
    """
    mock_logger: mock.Mock
    fake_print_controller: print_controller.PrintController

    def __init__(self):
        self.mock_logger = mock.Mock()
        self.test_printer = TestPrintController()

    def _fake_get_logger(self, module_name):
        self.mock_logger.module = module_name
        return self.mock_logger

    def __enter__(self):
        # A massive, ugly hack because mock.patch does not like actually replacing this function =(
        self._original_get_log_fn = print_controller.logging.getLogger
        print_controller.logging.getLogger = self._fake_get_logger

        self._original_global_printer = print_controller.PRINT_CONTROLLER
        print_controller.PRINT_CONTROLLER = self.test_printer
        return self

    def __exit__(self, *argv, **kwargs):
        print_controller.logging.getLogger = self._original_get_log_fn
        print_controller.PRINT_CONTROLLER = self._original_global_printer


if __name__ == '__main__':
    absltest.main()
