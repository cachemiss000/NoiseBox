import itertools
from schema import build_type_schema as buildschema
from mediaplayer import main as mediaplayer
from argparse import ArgumentParser
from common import flags

COMMANDS = {'buildschema': buildschema, 'mediaplayer': mediaplayer}


def command_flag(parser: ArgumentParser):
    parser.add_argument('command', choices=COMMANDS.keys(), help="The sub-tool to run.")


FLAGS = flags.FLAGS
flags.require(command_flag)


def main():
    command = COMMANDS.get(FLAGS.command)
    if not command:
        raise ValueError('Could not find input command')
    command.run()


if __name__ == '__main__':
    FLAGS.init()
    main()
