"""
Prints out JSON schema files for the commandserver to use as type hints by clients or other server implementations.
"""
from pathlib import Path

from absl import flags, app

from commandserver import command_types_v1 as v1

FLAGS = flags.FLAGS

flags.DEFINE_string("out", default=None, help="Defines the output directory in which files are placed.")


def print_v1():
    if not FLAGS.out:
        raise ValueError("--out must be set to build the schema.")
    relative_path_dir = Path(v1.__file__).relative_to(Path.cwd()).parent

    out_dir = Path.cwd().joinpath(FLAGS.out).joinpath(relative_path_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    v1.print_schema(out_dir.absolute())


def run(argv):
    print_v1()


if __name__ == '__main__':
    app.run(run)
