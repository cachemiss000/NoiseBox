import argparse
import unittest

from common import flags

FLAGS = flags.FLAGS


class TestFlags(unittest.TestCase):

    def setUp(self):
        super(TestFlags, self).setUp()
        FLAGS.reset()

    @staticmethod
    def register_flags(parser: argparse.ArgumentParser):
        parser.add_argument("--should_be_true", default=False)
        FLAGS._override_flags = ["--should_be_true", "True"]

    def test_flags(self):
        FLAGS.require(self.register_flags)
        FLAGS.init()
        self.assertTrue(FLAGS.should_be_true)

    def test_override_flag(self):
        FLAGS.require(self.register_flags)
        FLAGS.init()
        FLAGS.override_flag("should_be_true", "florgus")
        self.assertEqual(FLAGS.should_be_true, "florgus")

    def test_override_flag_context_management(self):
        FLAGS.require(self.register_flags)
        FLAGS.init()
        with FLAGS.override_flag("should_be_true", "florgus"):
            self.assertEqual(FLAGS.should_be_true, "florgus")
        self.assertTrue(FLAGS.should_be_true, True)

    def test_throws_no_init(self):
        FLAGS.require(self.register_flags)
        self.assertRaises(Exception, lambda: FLAGS.should_be_true)

    def test_requires(self):
        def fake_flag_fn():
            self.assertFalse(fake_flag_fn.ran)
            fake_flag_fn.ran = True

        fake_flag_fn.ran = False

        FLAGS.require(fake_flag_fn)
        FLAGS.require(fake_flag_fn)


if __name__ == '__main__':
    unittest.main()
