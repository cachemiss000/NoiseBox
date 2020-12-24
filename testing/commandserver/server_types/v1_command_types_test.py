import importlib
import inspect
import itertools
import re
import unittest
from collections import Set
from typing import Union, Type, Optional

from dataclasses_jsonschema import JsonSchemaMixin
from parameterized import parameterized

from commandserver.server_types import v1_command_types as types

MODULE_NAME = "v1_command_types"
MODULE_PATH = "commandserver.server_types." + MODULE_NAME


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

    def test_serializable_objects_all_extend_JSON_Mixin(self):
        bad_objects = []
        for object in itertools.chain(types.COMMANDS, types.EVENTS, types.OBJECTS):
            if not issubclass(object, JsonSchemaMixin):
                bad_objects.append(object)

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


def wrap_msg(obj: Union[types.EventCls, types.CommandCls]):
    if isinstance(obj, types.EventCls):
        return types.Event(message_name=obj.MESSAGE_NAME, payload=obj)
    if not isinstance(obj, types.CommandCls):
        raise ValueError("Expected Event or Command class object to wrap, got '%s'" % (obj.__name__,))
    return types.Command(message_name=obj.MESSAGE_NAME, payload=obj)


def default_song():
    return types.Song(name="Florgus", description="the florgust-y, blorgust-y beats",
                      metadata={"artist": "florgus-lover", "copyright": "2077"},
                      local_path="C:/florgus/blorgus/vorgus.mp3")


def default_playlist():
    return types.Playlist(name="florgus beats", description="The very best single tune you ever heard",
                          metadata={"timestamp": "2077-01-01", "creator": "TechnoFlorgus"},
                          songs=["Florgus"])


def get_default_event(event_t: Type[types.EventCls]) -> types.EventCls:
    if event_t == types.PlayStateEvent:
        return types.PlayStateEvent(new_play_state=True)
    if event_t == types.SongPlayingEvent:
        return types.SongPlayingEvent(current_song=default_song())
    if event_t == types.ListSongsEvent:
        return types.ListSongsEvent([default_song()])
    if event_t == types.ListPlaylistsEvent:
        return types.ListPlaylistsEvent([default_playlist()])
    if event_t == types.ErrorEvent:
        return types.ErrorEvent(error_message="Not enough florgus in your tunes",
                                error_type=types.ErrorType.CLIENT_ERROR,
                                error_data="Get more florgus. Nao.",
                                error_env=types.ErrorDataEnv.DEBUG,
                                originating_command=str(types.Command(
                                    message_name=types.NextSongCommand.MESSAGE_NAME,
                                    payload=types.NextSongCommand())))
    raise ValueError("Couldn't determine default event for event type '%s' =(" % (event_t,))


def get_default_command(command_t: Type[types.CommandCls]) -> types.CommandCls:
    if command_t == types.TogglePlayCommand:
        return types.TogglePlayCommand(play_state=False)
    if command_t == types.NextSongCommand:
        return types.NextSongCommand()
    if command_t == types.ListSongsCommand:
        return types.ListSongsCommand()
    if command_t == types.ListPlaylistsCommand:
        return types.ListPlaylistsCommand()
    raise ValueError("Couldn't determine default command for command type '%s' =(" % (command_t,))


class TestHelperTypes(unittest.TestCase):

    def test_api_works_without_metaprogramming_or_introspection_garbage(self):
        # This is just a sanity check to make sure the API remains readable when you're not doing
        # metaprogramming garbage like the rest of these tests.

        class EventRouter(types.EventTypeMap):
            def __init__(self):
                self.play_state_calls = 0
                self.song_playing_calls = 0
                self.play_state_event: Optional[types.EventCls] = None
                self.song_playing_event: Optional[types.EventCls] = None

            def with_play_state(self, event: types.PlayStateEvent):
                self.play_state_event = event
                self.play_state_calls += 1

            def with_song_playing(self, event: types.SongPlayingEvent):
                self.song_playing_event = event
                self.song_playing_calls += 1

        event_map = EventRouter()
        play_state_event = get_default_event(types.PlayStateEvent)
        play_state_msg = wrap_msg(play_state_event)
        event_map.handle_message(play_state_msg)
        event_map.handle_message(play_state_msg)

        song_playing_event = get_default_event(types.SongPlayingEvent)
        song_playing_msg = wrap_msg(song_playing_event)
        event_map.handle_message(song_playing_msg)
        event_map.handle_message(song_playing_msg)
        event_map.handle_message(song_playing_msg)

        self.assertEqual(event_map.play_state_calls, 2)
        self.assertEqual(event_map.song_playing_calls, 3)
        self.assertEqual(event_map.play_state_event, play_state_event)
        self.assertEqual(event_map.song_playing_event, song_playing_event)

    @parameterized.expand([(x,) for x in types.EVENTS])
    def test_expect_events(self, event_t: Type[types.EventCls]):
        event = get_default_event(event_t)

        def handler_func(this_event: types.EventCls):
            handler_func.called_count += 1
            handler_func.event = this_event

        handler_func.called_count = 0
        handler_func.event = None

        create_expect_cls_func = getattr(types.EventTypeMap, "expect_%s" % (event_t.MESSAGE_NAME.lower(),))
        expect_map = create_expect_cls_func(handler_func)
        expect_map.handle_message(wrap_msg(event))

        self.assertEqual(handler_func.called_count, 1)
        self.assertEqual(handler_func.event, event)

    @parameterized.expand([(x,) for x in types.COMMANDS])
    def test_expect_commands(self, command_t: Type[types.CommandCls]):
        command = get_default_command(command_t)

        def handler_func(this_command: types.CommandCls):
            handler_func.called_count += 1
            handler_func.command = this_command

        handler_func.called_count = 0
        handler_func.command = None

        expect_map = types.CommandTypeMap.expect(command_t, handler_func)
        expect_map.handle_message(wrap_msg(command))

        self.assertEqual(handler_func.called_count, 1)
        self.assertEqual(handler_func.command, command)

    @parameterized.expand([(x,) for x in types.EVENTS])
    def test_expect_event_fails_on_unexpected_event(self, event_t: Type[types.EventCls]):
        def handler_func(event_c: types.EventCls):
            raise TypeError(
                "Got the expected type '%s', which is - counterintuitively, unexpected" % (event_c.MESSAGE_NAME,))

        expect_map = types.EventTypeMap.expect(event_t, handler_func)
        for unexpected_event_t in types.EVENTS.difference({event_t}):
            with self.assertRaisesRegex(ValueError, r'.*event.*%s' % (unexpected_event_t.MESSAGE_NAME,)):
                expect_map.handle_message(wrap_msg(get_default_event(unexpected_event_t)))

    @parameterized.expand([(x,) for x in types.COMMANDS])
    def test_expect_command_fails_on_unexpected_command(self, command_t: Type[types.CommandCls]):
        def handler_func(command_c: types.CommandCls):
            raise TypeError(
                "Got the expected type '%s', which is, counterintuitively, unexpected" % (command_c.MESSAGE_NAME,))

        expect_map = types.CommandTypeMap.expect(command_t, handler_func)
        for unexpected_command_t in types.COMMANDS.difference({command_t}):
            with self.assertRaisesRegex(ValueError, r'.*command.*%s' % (unexpected_command_t.MESSAGE_NAME,)):
                expect_map.handle_message(wrap_msg(get_default_command(unexpected_command_t)))

    def test_events_throws_for_bad_input(self):
        def handler_func(event_c: types.EventCls):
            raise Exception("Didn't expect to get here =(. Event '%s'" % (event_c,))

        expect_play_state = types.EventTypeMap.expect_play_state(handler_func)

        bad_event = types.Event("PLAY_STATE", types.SongPlayingEvent())

        with self.assertRaisesRegex(TypeError, r".*SongPlayingEvent.*PlayStateEvent.*"):
            expect_play_state.handle_message(bad_event)

    def test_commands_throws_for_bad_input(self):
        def handler_func(command_c: types.CommandCls):
            raise Exception("Didn't expect to get here =(. Command '%s'" % (command_c,))

        expect_toggle_play = types.CommandTypeMap.expect_toggle_play(handler_func)

        bad_command = types.Command("TOGGLE_PLAY", get_default_command(types.NextSongCommand))

        with self.assertRaisesRegex(TypeError, r".*NextSongCommand.*TogglePlayCommand.*"):
            expect_toggle_play.handle_message(bad_command)

    def test_events_works_with_valid_json(self):
        event_c = get_default_event(types.SongPlayingEvent)

        def handler_func(this_event_c: types.EventCls):
            self.assertEqual(this_event_c, event_c)
            handler_func.called += 1
            handler_func.event_c = this_event_c
            return handler_func.called

        handler_func.called = 0
        handler_func.event_c = None

        event_msg = types.Event.from_json(types.Event(message_name="SONG_PLAYING", payload=event_c).to_json())
        expect_song_playing = types.EventTypeMap.expect_song_playing(handler_func)

        r1 = expect_song_playing.handle_message(event_msg)
        r2 = expect_song_playing.handle_message(event_msg)
        r3 = expect_song_playing.handle_message(event_msg)

        self.assertEqual(r1, 1)
        self.assertEqual(r2, 2)
        self.assertEqual(r3, 3)
        self.assertEqual(handler_func.called, 3)
        self.assertEqual(handler_func.event_c, event_c)

    def test_commands_works_with_valid_json(self):
        command_c = get_default_command(types.TogglePlayCommand)

        def handler_func(this_command: types.CommandCls):
            self.assertEqual(this_command, command_c)
            handler_func.called += 1
            handler_func.command_c = this_command
            return handler_func.called

        handler_func.called = 0
        handler_func.command_c = None

        command_msg = types.Command(message_name="TOGGLE_PLAY", payload=command_c.to_json())
        expect_toggle_play = types.CommandTypeMap.expect_toggle_play(handler_func)

        r1 = expect_toggle_play.handle_message(command_msg)
        r2 = expect_toggle_play.handle_message(command_msg)
        r3 = expect_toggle_play.handle_message(command_msg)

        self.assertEqual(r1, 1)
        self.assertEqual(r2, 2)
        self.assertEqual(r3, 3)
        self.assertEqual(handler_func.called, 3)
        self.assertEqual(handler_func.command_c, command_c)

    def test_events_works_with_valid_dict(self):
        event = get_default_event(types.SongPlayingEvent)

        def handler_func(this_event: types.EventCls):
            handler_func.event_c = this_event
            handler_func.called += 1
            return handler_func.called

        handler_func.called = 0
        handler_func.event_c = None

        event_msg = types.Event(message_name="SONG_PLAYING", payload=event.to_dict())
        expect_song_playing = types.EventTypeMap.expect_song_playing(handler_func)

        r1 = expect_song_playing.handle_message(event_msg)
        r2 = expect_song_playing.handle_message(event_msg)
        r3 = expect_song_playing.handle_message(event_msg)

        self.assertEqual(r1, 1)
        self.assertEqual(r2, 2)
        self.assertEqual(r3, 3)
        self.assertEqual(handler_func.called, 3)
        self.assertEqual(handler_func.event_c, event)

    def test_commands_works_with_valid_dict(self):
        command_c = get_default_command(types.TogglePlayCommand)

        def handler_func(this_command: types.CommandCls):
            self.assertEqual(this_command, command_c)
            handler_func.called += 1
            return handler_func.called

        handler_func.called = 0

        command_msg = types.Command(message_name="TOGGLE_PLAY", payload=command_c.to_dict())
        expect_toggle_play = types.CommandTypeMap.expect_toggle_play(handler_func)

        r1 = expect_toggle_play.handle_message(command_msg)
        r2 = expect_toggle_play.handle_message(command_msg)
        r3 = expect_toggle_play.handle_message(command_msg)

        self.assertEqual(r1, 1)
        self.assertEqual(r2, 2)
        self.assertEqual(r3, 3)
        self.assertEqual(handler_func.called, 3)

    def test_events_works_with_valid_event_c(self):
        event_c = get_default_event(types.SongPlayingEvent)

        def handler_func(this_event: types.EventCls):
            self.assertEqual(this_event, event_c)
            handler_func.called += 1
            return handler_func.called

        handler_func.called = 0

        event_msg = types.Event(message_name="SONG_PLAYING", payload=event_c)
        expect_song_playing = types.EventTypeMap.expect_song_playing(handler_func)

        r1 = expect_song_playing.handle_message(event_msg)
        r2 = expect_song_playing.handle_message(event_msg)
        r3 = expect_song_playing.handle_message(event_msg)

        self.assertEqual(r1, 1)
        self.assertEqual(r2, 2)
        self.assertEqual(r3, 3)
        self.assertEqual(handler_func.called, 3)

    def test_commands_works_with_valid_command_c(self):
        command_c = get_default_command(types.TogglePlayCommand)

        def handler_func(this_command: types.CommandCls):
            self.assertEqual(this_command, command_c)
            handler_func.called += 1
            return handler_func.called

        handler_func.called = 0

        command_msg = types.Command(message_name="TOGGLE_PLAY", payload=command_c)
        expect_toggle_play = types.CommandTypeMap.expect_toggle_play(handler_func)

        r1 = expect_toggle_play.handle_message(command_msg)
        r2 = expect_toggle_play.handle_message(command_msg)
        r3 = expect_toggle_play.handle_message(command_msg)

        self.assertEqual(r1, 1)
        self.assertEqual(r2, 2)
        self.assertEqual(r3, 3)
        self.assertEqual(handler_func.called, 3)


def get_test_module_classes():
    name_class_tuples = list(inspect.getmembers(importlib.import_module(MODULE_PATH)))
    only_classes = [(name, cls) for name, cls in name_class_tuples if inspect.isclass(cls)]
    from_right_module = [(name, cls) for name, cls in only_classes if
                         hasattr(cls, "__module__") and cls.__module__ == MODULE_PATH]
    return from_right_module


if __name__ == '__main__':
    unittest.main()
