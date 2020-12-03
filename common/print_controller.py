"""
This module implements a number of methods of printing to various locations.

In particular, it implements a SystemPrintController and a MetaPrintController
so that we can log to a file while also recording a commandline session to a file (for instance)
with minimal disruption to the actual flow of programming code.
"""
import logging


class PrintController(object):
    def print(self, message, *args):
        """Prints a message to wherever the class points."""
        pass


class SystemPrintController(PrintController):
    """Prints messages to stdout."""

    def print(self, message, *args):
        print(message, *args)


class MetaPrintController(PrintController):
    """Prints to multiple PrintController objects whenever print() is called."""

    def __init__(self):
        self.controllers = []

    def add_print_controller(self, print_controller: PrintController):
        """Adds a new print controller to the list to which output gets sent."""
        self.controllers.append(print_controller)

    def print(self, message, *args):
        for controller in self.controllers:
            controller.print(message, *args)


PRINT_CONTROLLER = MetaPrintController()
PRINT_CONTROLLER.add_print_controller(SystemPrintController())


class PrintingLogger(PrintController):
    def __init__(self, module_name, min_error_level_to_print: int = logging.WARNING,
                 passthrough_printer: PrintController = PRINT_CONTROLLER):
        self.module_name = module_name
        self.logger = logging.getLogger(self.module_name)
        self.min_error_level_to_print = min_error_level_to_print
        self.passthrough_printer = passthrough_printer

    def log(self, error_level: int, message, *argv):
        if error_level >= self.min_error_level_to_print:
            self.passthrough_printer.print(
                "%s - %s: %s" % (self.module_name, logging.getLevelName(error_level), message), *argv)
        self.logger.log(error_level, message, *argv)

    def debug(self, message: str, *argv):
        self.log(logging.DEBUG, message, *argv)

    def info(self, message: str, *argv):
        self.log(logging.INFO, message, *argv)

    def warn(self, message: str, *argv):
        self.log(logging.WARN, message, *argv)

    def error(self, message: str, *argv):
        self.log(logging.ERROR, message, *argv)

    def critical(self, message: str, *argv):
        self.log(logging.CRITICAL, message, *argv)


class _GlobalPassthroughController(PrintController):
    def print(self, msg: str, *argv):
        print_msg(msg, *argv)


def logging_printer(module_name: str, min_error_level_to_print: int = logging.WARNING):
    return PrintingLogger(module_name, min_error_level_to_print, _GlobalPassthroughController())


def add_print_controller(print_controller: PrintController):
    """Module-level function used to add print controllers so module clients don't need to muck with constants."""
    PRINT_CONTROLLER.add_print_controller(print_controller)


def print_msg(message, *argv):
    """Prints a message to the built-in print controller."""
    PRINT_CONTROLLER.print(message, *argv)
