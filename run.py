from absl import flags, app

from build_schema import build_type_schema as buildschema
from mediaplayer import main as mediaplayer

FLAGS = flags.FLAGS

COMMANDS = {'buildschema': buildschema, 'mediaplayer': mediaplayer}

flags.DEFINE_string('command', default='', help="The sub-tool to run.")
flags.register_validator('command', lambda flag: flag in COMMANDS.keys() or not flag,
                         message="Expected command flag to be in '%s'" % (', '.join([k for k in COMMANDS.keys()]),))


def main(argv):
    command_str = FLAGS.command
    if not command_str and len(argv):
        command_str = argv[1]
    command = COMMANDS.get(command_str)
    if not command:
        raise ValueError('Could not find input command')
    command.run(argv)


if __name__ == '__main__':
    app.run(main)
