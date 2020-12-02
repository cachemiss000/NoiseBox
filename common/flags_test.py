import unittest
import argparse
import sys

from common import flags

FLAGS = flags.FLAGS


class TestFlags(unittest.TestCase):
    @staticmethod
    def register_flags(parser: argparse.ArgumentParser):
        parser.add_argument("--should_be_true", default=False)
        FLAGS._override_flags = ["--should_be_true", "True"]

    def test_flags(self):
        FLAGS.register_flags(self.register_flags)
        self.assertTrue(FLAGS.should_be_true)


if __name__ == '__main__':
    unittest.main()
