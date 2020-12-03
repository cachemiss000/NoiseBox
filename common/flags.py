"""
A poor man's GFlags module. Provides global flag parsing when mixing many modules together.

USAGE:
  import flags

  FLAGS = flags.FLAGS

  FLAGS.register_flags(lambda parser: <add your arguments using the parser here>)
  FLAGS.register_flag(<Use like "parser.add_argument>)

  def my_function(...):
    flag_value = FLAGS.whatever_flag_you_defined  # DO NOT access defined flags from the global scope!



Rational:
 * Why not use GFlags directly? I don't want to add the extra heavy dependency
 * Why not just make a global file at the root directory of a binary? This will allow modules to define their own flags

Contraindications:
 * DO NOT use in others' binaries. Only for use in "NoiseBox" binaries.
 * DO NOT set _override_flags unless working in test code.
 * AVOID setting/registering flags outside the global scope.
"""
import argparse
import sys
from typing import Callable


class _FlagNamespaceContainer:
    """Holds the list of flag-defining functions to call, and acts as a namespace for sys.argv flags."""

    def __init__(self):
        self._flag_namespace = None
        self.flag_function_registry = set()

        # Used to override sys.argv for testing.
        # An array of strings. Typically unset, except in the FLAGS unittest. Other tests should use
        # the override_flags() method.
        self._override_flags = None

    def __getattr__(self, name):
        # We get this case once when the program starts, because
        # _memoized_value gets set by _process_flags().
        if self._flag_namespace is None:
            raise AttributeError('FLAGS has not been initialized yet. Please call FLAGS.init() in your Main method.')
        if name not in self._flag_namespace:
            raise AttributeError("'%s' not defined as a flag" % (name,))

        return self._flag_namespace.__getattribute__(name)

    def init(self):
        """Add all registered flags to "this" namespace.

        Can be called multiple times. Call "FLAGS.reset()" to undo.
        """
        parser = argparse.ArgumentParser()
        for fn in self.flag_function_registry:
            fn(parser)
        flags_to_parse = sys.argv if not self._override_flags else self._override_flags
        if 'unittest' in flags_to_parse[0]:  # ex: "python -m unittest"
            # We're being run as part of the unittest framework. Quick hack out bad flags
            try:
                post_idx = flags_to_parse.index("--")
                flags_to_parse = flags_to_parse[post_idx + 1:]
            except ValueError:
                flags_to_parse = []  # Did not find the '--' after which we should pull flags
        self._flag_namespace = parser.parse_args(args=flags_to_parse)

    def require(self, flag_fn: Callable):
        """Call a function to configure flags in the namespace."""
        if self._flag_namespace is not None:
            raise Exception("Cannot add flags after flags have been retrieved."
                            "Did you try to access a FLAGS value at the global scope? "
                            "(hint: don't do that.)")
        if flag_fn in self.flag_function_registry:
            return

        self.flag_function_registry.add(flag_fn)

    def register_flag(self, **kwargs):
        """Register a singular flag as with ArgumentParser.add_argument(...)"""
        self.register_flags(lambda parser: parser.add_argument(**kwargs))

    def override_flag(self, key, value):
        """Override a flag key/value pair for a test.

        Works as a context manager with "with" statements to 'unset' changed flags, for individual test cases.
        """

        old_value = self._flag_namespace.__getattribute__(key)
        instance = self

        class _OverrideContextManager:
            """Quick and dirty context manager, using scope capture for state management."""

            def __enter__(self):
                yield

            def __exit__(self, *args):
                instance._flag_namespace.__setattr__(key, old_value)

        self._flag_namespace.__setattr__(key, value)
        return _OverrideContextManager()

    def reset(self):
        self._flag_namespace = None
        self.flag_function_registry = set()
        self._override_flags = []


FLAGS = _FlagNamespaceContainer()


def require(flag_fn: Callable):
    return FLAGS.require(flag_fn)


def init():
    return FLAGS.init()
