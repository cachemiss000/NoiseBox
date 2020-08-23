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
    def __init__(self, name: str, arg_parser: ArgumentParser):
        self.__name = name.lower()
        self.arg_parser = arg_parser

    def process(self, argv: List[str]):
        logger.info("Processing command: %s - '%s", self.__name,  argv)
        self.do_function(**vars(self.arg_parser.parse_args(args=argv)))

    @abstractmethod
    def do_function(self, **arg_dict):
        raise UnimplementedException()

    def help_string(self) -> str:
        return self.arg_parser.format_help()

    @property
    def name(self):
        return self.__name.lower()
