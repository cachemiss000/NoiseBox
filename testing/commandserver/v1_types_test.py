import importlib
import inspect
import itertools
import re
import unittest
from collections import Set

from dataclasses_jsonschema import JsonSchemaMixin

from commandserver import command_types_v1 as types

MODULE_NAME = "command_types_v1"
MODULE_PATH = "commandserver." + MODULE_NAME


class SanityTest(unittest.TestCase):

    def test_commands_responses_match(self):
        self.assertEqual(len(types.COMMANDS), len(types.RESPONSES),
                         "Expected there to be an equal number of commands and responses.\n"
                         "If you have a command, that command needs a response - even if it's empty.\n"
                         "Make sure to add a response, then add that response class to the list at the\n"
                         "bottom of the file.\n"
                         "\n"
                         "Command count: '%s', Response count: '%s'\n"
                         "\n"
                         "Missing Commands: '%s'\n"
                         "MissingResponses: '%s'" % (
                             len(types.COMMANDS), len(types.RESPONSES), types.COMMANDS, types.RESPONSES))

    def test_commands_responses_naming(self):
        bad_commands = []
        for command_cls in types.COMMANDS:
            command_name = command_cls.__name__
            if not re.match(r'.*Command$', command_name):
                bad_commands.append(command_name)

        bad_responses = []
        for response_cls in types.RESPONSES:
            response_name = response_cls.__name__
            if not re.match(r'.*Response$', response_name):
                bad_responses.append(response_name)

        self.assertFalse(bad_commands + bad_responses, "\n\nExpected the list to be empty. list is populated with\n"
                                                       "command names that don't end in 'Command'.\n"
                                                       "Make sure the objects in 'COMMANDS' are all supposed to be there.")

    def test_serializable_objects_all_extend_JSON_Mixin(self):
        bad_objects = []
        for object in itertools.chain(types.COMMANDS, types.RESPONSES, types.OBJECTS):
            if not issubclass(object, JsonSchemaMixin):
                bad_objects.append(object)

        self.assertFalse(bad_objects,
                         "\n\nExpected the following objects to extend the JsonSchemaMixin class. This is necessary\n"
                         "to ensure that the class schema can get printed out for data validation on the\n"
                         "client side before sending. Please update the class definition.\n\n'%s'" % (bad_objects,))

    def test_all_objects_accounted_for(self):
        missing_objects = set()
        schema_exported_objects: Set[object] = set(itertools.chain(
            types.OBJECTS, types.COMMANDS, types.RESPONSES, types._IGNORE_OBJECTS))
        for name, cls in get_test_module_classes():
            if cls not in schema_exported_objects:
                missing_objects.add(name)

        self.assertFalse(missing_objects,
                         "\n\nThe following objects are not accounted for in schema-documenting objects.\n"
                         "This includes the 'OBJECTS', 'COMMANDS', 'RESPONSES' lists, as well as the\n"
                         "_IGNORE_OBJECTS list, the last of which is responsible for objects that do\n"
                         "not show up in the outward facing schema. Please file the object in the right\n"
                         "object.\n    '%s'" % (missing_objects,))


def get_test_module_classes():
    name_class_tuples = list(inspect.getmembers(importlib.import_module(MODULE_PATH)))
    only_classes = [(name, cls) for name, cls in name_class_tuples if inspect.isclass(cls)]
    from_right_module = [(name, cls) for name, cls in only_classes if
                         hasattr(cls, "__module__") and cls.__module__ == MODULE_PATH]
    return from_right_module

if __name__ == '__main__':
    unittest.main()
