"""
Implements the Command class, in order to aid commandline processing.
"""
import logging
from abc import abstractmethod
from typing import List
from argparse import ArgumentParser

logger = logging.getLogger("media-player")


class InvalidCommandUseException(Exception):
    pass


class UnimplementedException(Exception):
    pass


class Command(object):
    """A base class for commandline commands.

    You can find extensive use of the Command class in commands.py.
    """
    def __init__(self, name: str, arg_parser: ArgumentParser):
        """Constructor for command

        :param name: The name for this command that the user types in on the command line to call this command.
        :param arg_parser: An arg parser to use when parsing the argv in 'process()'. It'll split out the
          individual arguments from the commandline string ["--output=foo", "--input=bar"] into an argument dict
          like {output: 'foo', input: 'bar'}
        """
        self.__name = name.lower()
        self.arg_parser = arg_parser

    def process(self, argv: List[str]):
        """If it's determined that the caller meant to call this command, this function will call the command logic.

        argv: Input string arguments from the command line.
        """
        logger.info("Processing command: %s - '%s", self.__name,  argv)
        self.do_function(**vars(self.arg_parser.parse_args(args=argv)))

    @abstractmethod
    def do_function(self, **arg_dict):
        """Base method for the command. Subclasses should implement this function with whatever they're supposed to do

        :param arg_dict: The dict of arguments parsed from the commandline by the arg_parser passed in during
         initialization.
        """
        raise UnimplementedException()

    def help_string(self) -> str:
        """Returns a help string to print out on the command line."""
        return self.arg_parser.format_help()

    @property
    def name(self):
        """Name of the command. Used in main.py to map console strings to Command implementations."""
        return self.__name.lower()
