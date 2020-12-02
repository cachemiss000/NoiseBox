"""
This module implements a number of methods of printing to various locations.

In particular, it implements a SystemPrintController and a MetaPrintController
so that we can log to a file while also recording a commandline session to a file (for instance)
with minimal disruption to the actual flow of programming code.
"""


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


def add_print_controller(print_controller: PrintController):
    """Module-level function used to add print controllers so module clients don't need to muck with constants."""
    PRINT_CONTROLLER.add_print_controller(print_controller)


def print_msg(message, *argv):
    """Prints a message to the built-in print controller."""
    PRINT_CONTROLLER.print(message, *argv)
