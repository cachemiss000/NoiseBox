from typing import Dict

from common.command import Command
from common.safe_arg_parse import SafeArgumentParser
from common.print_controller import print_msg


class Help(Command):
    """Gets help for a given command."""
    def __init__(self, command_dict: Dict[str, Command]):
        ap = SafeArgumentParser("Get help on any command")
        ap.add_argument("command", nargs='?', help="the command on which to receive help")
        super().__init__(name="help", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self, command=""):
        if command is None:
            print_msg(self.help_string())
            return
        if command not in self.command_dict:
            print_msg(
                "Cannot find command '%s'.\n\nAvailable commands: '%s'" % (command, self.command_dict.keys()))
            return
        print_msg(self.command_dict[command].help_string())
        return


class ListCommands(Command):
    """Lists all commands."""
    def __init__(self, command_dict: Dict[str, Command]):
        ap = SafeArgumentParser("List commands")
        super().__init__(name="commands", arg_parser=ap)
        self.command_dict = command_dict

    def do_function(self):
        print_msg("Available commands: [\n  %s\n]" % ("\n  ".join(self.command_dict)))