import importlib
import inspect
import itertools
import json
import re
import unittest
from collections import Set

from parameterized import parameterized
from pydantic import BaseModel, ValidationError

from commandserver.server_types import v1_command_types as types
from common.test_utils import get_default_command, get_default_event, default_song

MODULE_NAME = "v1_command_types"
MODULE_PATH = "commandserver.server_types." + MODULE_NAME


class ParsingTest(unittest.TestCase):

    def test_event_name_unset(self):
        message = {
            "event": {
                "error_message": "errors go burrrrr"
            }
        }

        with self.assertRaises(ValidationError) as e:
            types.Message.parse_raw(json.dumps(message))

    def test_command_name_unset(self):
        message = {
            "command": {
                "play_state": True
            }
        }

        with self.assertRaises(ValidationError) as e:
            types.Message.parse_raw(json.dumps(message))



class SanityTest(unittest.TestCase):

    def test_commands_responses_naming(self):
        bad_commands = []
        for command_t in types.COMMANDS:
            command_name = command_t.__name__
            if not re.match(r'.*Command$', command_name):
                bad_commands.append(command_name)

        bad_events = []
        for event_t in types.EVENTS:
            event_name = event_t.__name__
            if not re.match(r'.*Event$', event_name):
                bad_events.append(event_name)

        self.assertFalse(bad_commands + bad_events,
                         "\n\nExpected the list to be empty. list is populated with\n"
                         "command & event names that don't end in 'Command' or 'Event' respectively.\n"
                         "Make sure the objects in 'COMMANDS' are all supposed to be there.")

    def test_serializable_objects_all_extend_BaseModel(self):
        bad_objects = []
        for serializable_object in itertools.chain(types.COMMANDS, types.EVENTS, types.OBJECTS):
            if not issubclass(serializable_object, BaseModel):
                bad_objects.append(serializable_object)

        self.assertFalse(bad_objects,
                         "\n\nExpected the following objects to extend the JsonSchemaMixin class. This is necessary\n"
                         "to ensure that the class schema can get printed out for data validation on the\n"
                         "client side before sending. Please update the class definition.\n\n'%s'" % (bad_objects,))

    def test_all_objects_accounted_for(self):
        missing_objects = set()
        schema_exported_objects: Set[object] = set(itertools.chain(
            types.OBJECTS, types.COMMANDS, types.EVENTS, types._IGNORE_OBJECTS))
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


class TypeValidationTest(unittest.TestCase):
    def test_command_event_set_xor(self):
        c = get_default_command(types.TogglePlayCommand)
        e = get_default_event(types.ListSongsEvent)

        with self.assertRaises(ValidationError):
            types.Message(**{
                'event': e,
                'command': c
            })

        with self.assertRaises(ValidationError):
            types.Message()

    def test_wrap_command_with_fields(self):
        """Wrap happens at the Command class level, so we don't need to test individually"""
        c = types.TogglePlayCommand(command_name=types.TogglePlayCommand.COMMAND_NAME, play_state=True)
        self.assertEqual(c.wrap(), types.Message(**{
            'command': {
                'command_name': types.TogglePlayCommand.COMMAND_NAME,
                'play_state': True
            }
        }))

    def test_wrap_command_no_fields(self):
        """Wrap happens at the Command class level, so we don't need to test individually."""
        c = types.NextSongCommand(command_name=types.NextSongCommand.COMMAND_NAME)
        self.assertEqual(c.wrap(), types.Message(**{
            'command': {
                'command_name': types.NextSongCommand.COMMAND_NAME
            }
        }))

    def test_wrap_event_with_fields(self):
        """Wrap happens at the Event class level, so we don't need to test individually"""
        e = types.ErrorEvent(
            event_name=types.ErrorEvent.EVENT_NAME, error_message="everything is on fire",
            error_type=types.ErrorType.CLIENT_ERROR, error_env=types.ErrorDataEnv.DEBUG)

        self.assertEqual(e.wrap(), types.Message(**{
            'event': {
                'event_name': types.ErrorEvent.EVENT_NAME,
                'error_message': 'everything is on fire',
                'error_type': types.ErrorType.CLIENT_ERROR,
                'error_env': types.ErrorDataEnv.DEBUG
            }
        }))

    def test_wrap_event_without_fields(self):
        """Wrap happens at the Event class level, so we don't need to test individually"""
        e = types.ListSongsEvent(event_name=types.ListSongsEvent.EVENT_NAME)

        self.assertEqual(e.wrap(), types.Message(**{
            'event': {
                'event_name': types.ListSongsEvent.EVENT_NAME
            }
        }))

    def test_command_unwrap(self):
        c = types.TogglePlayCommand(command_name=types.TogglePlayCommand.COMMAND_NAME, play_state=True)
        msg = c.wrap()
        self.assertEqual(msg.unwrap(types.TogglePlayCommand), c)

    def test_event_unwrap(self):
        e = types.ListSongsEvent(event_name=types.ListSongsEvent.EVENT_NAME, songs=[default_song()])
        msg = e.wrap()
        self.assertEqual(msg.unwrap(types.ListSongsEvent), e)

    def test_command_unwrap_bad_type(self):
        c = types.TogglePlayCommand(command_name=types.TogglePlayCommand.COMMAND_NAME)
        msg = c.wrap()
        with self.assertRaises(TypeError):
            msg.unwrap(types.ListSongsCommand)

    def test_event_unwrap_bad_type(self):
        e = types.ListSongsEvent(event_name=types.ListSongsEvent.EVENT_NAME, songs=[default_song()])
        msg = e.wrap()
        with self.assertRaises(TypeError):
            msg.unwrap(types.PlayStateEvent)

    @parameterized.expand((msg_type,) for msg_type in itertools.chain(types.EVENTS, types.COMMANDS))
    def test_create(self, msg_type):
        m = msg_type.create()
        self.assertIsInstance(m, msg_type)


if __name__ == '__main__':
    unittest.main()
