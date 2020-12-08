"""
Prints out JSON schema files for the commandserver to use as type hints by clients or other server implementations.
"""
import argparse
from pathlib import Path
from commandserver import command_types_v1 as v1

from common import flags

FLAGS = flags.FLAGS


def build_flags(parser: argparse.ArgumentParser):
    parser.add_argument("--out", default="./", help="Defines the output directory in which files are placed.")


def print_v1():
    relative_path_dir = Path(v1.__file__).relative_to(Path.cwd()).parent

    out_dir = Path.cwd().joinpath(FLAGS.out).joinpath(relative_path_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    v1.print_schema(out_dir.absolute())


def run():
    FLAGS.init()
    print_v1()


FLAGS.require(build_flags)

if __name__ == '__main__':
    run()
