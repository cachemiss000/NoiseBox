import argparse

from localcli.print_controller import print_msg


class SafeArgumentParser(argparse.ArgumentParser):
    """This handles errors for argparse, so errors get printed out to the commandline console."""
    def error(self, message):
        print_msg(message)