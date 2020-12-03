import argparse
import logging


class ParseLogLevelAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs is not allowed")
        super(ParseLogLevelAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, logging._levelToName.get(values))


def flags(parser: argparse.ArgumentParser):
    parser.add_argument('--debug', type=bool, default=False,
                        help='Run the server in debug mode. Provides messy-but-debug-friendly output. '
                             'Not recommended for end users.')

    parser.add_argument('--run_version', type=str, nargs='+', default='v1',
                        help='versions to run. Currently supported: [V1]')

    parser.add_argument('--server_log_level', type=int, default=logging.WARN, action=ParseLogLevelAction,
                        help='The log level at which the command server should start printing out messages.')
