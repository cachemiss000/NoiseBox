import unittest
from dataclasses import dataclass
from typing import List, Type

from absl.testing import absltest
from parameterized import parameterized

from messages.message_map import MessageCls, MessageMapTypeHints, message_map, _expect_function_name, Message, \
    _with_function_name


@dataclass
class ItemNameAndNumber(MessageCls):
    MESSAGE_NAME = "NAME_AND_NUMBER"

    item_name: str
    item_number: int


@dataclass
class ItemColor(MessageCls):
    MESSAGE_NAME = "COLOR"

    item_color: str


@dataclass
class ItemSize(MessageCls):
    MESSAGE_NAME = "SIZE"

    size_units: str
    item_size: int


ITEM_DESCRIPTORS: List[Type[MessageCls]] = [ItemNameAndNumber, ItemColor, ItemSize]


@message_map(message_name="item", message_types=ITEM_DESCRIPTORS)
class ItemMap(MessageMapTypeHints):
    pass


class TestExpect(unittest.TestCase):

    @parameterized.expand([(t,) for t in ITEM_DESCRIPTORS])
    def test_expect_behaves_correctly_for_all_types(self, message_t: Type[MessageCls]):
        """Tests each message type defined at the top of this file to ensure that expect beahves correctly.

        IoW: It throws for unexpected items, and calls the provided method for the correct item.
        """

        def expect_item(item: message_t):
            if not isinstance(item, message_t):
                raise ValueError("Wrong item received. Got %s, expected type %s" % (item, message_t))
            expect_item.received_item = item

        expect_item.received_item = None

        size_item = ItemSize(size_units="meters", item_size=1523)
        color_item = ItemColor(item_color="mauve")
        name_number_item = ItemNameAndNumber(item_name="florgus", item_number=99666699)
        items = [size_item, color_item, name_number_item]

        unexpected_items = [item for item in items if type(item) != message_t]
        expected_item = next(item for item in items if type(item) == message_t)
        expect_map: MessageMapTypeHints = ItemMap.expect(message_t, expect_item)

        # Note: We kinda mix "act" and "assert" blocks here because there's no other great way to do it.
        # Oh well.
        expect_map.with_msg(message_t, expected_item)

        for item in unexpected_items:
            with self.assertRaises(ValueError) as e:
                expect_map.with_msg(type(item), item)
            self.assertRegex(str(e.exception), "Did not expect")
        self.assertEqual(expect_item.received_item, expected_item)

    def test_expect_returns_function_return_value(self):
        return_size = ItemSize(size_units='kilograms', item_size=666)

        def expect_item(_item: ItemColor):
            return return_size

        expect_map = ItemMap.expect(ItemColor, expect_item)
        return_value = expect_map.with_msg(ItemColor, ItemColor("black of darkest night"))

        self.assertEqual(return_value, return_size)

    def test_expect_throws_on_wrong_expect_type(self):
        @dataclass
        class NewItem(MessageCls):
            MESSAGE_NAME = "NEW_ITEM"
            date_created: str

        def dummy(_item: NewItem):
            pass

        with self.assertRaises(TypeError) as e:
            ItemMap.expect(NewItem, dummy)
        self.assertRegex(str(e.exception),
                         ".*Expected type in 'ItemNameAndNumber, ItemColor, ItemSize', got 'NewItem'.*")

    def test_expect_none_type(self):
        def dummy(_):
            pass

        with self.assertRaises(TypeError):
            ItemMap.expect(None, dummy)

    def test_expect_noncallable_handler(self):
        item = ItemSize("angstroms", item_size=1)
        with self.assertRaises(TypeError):
            ItemMap.expect(ItemSize, item)

    def test_expect_doesnt_get_built_when_false(self):
        @message_map(message_types=ITEM_DESCRIPTORS, build_expect=False)
        class NoExpectMap(MessageMapTypeHints):
            pass

        with self.assertRaises(NotImplementedError):
            NoExpectMap.expect(ItemSize, lambda x: 'meh.')

        for item in ITEM_DESCRIPTORS:
            self.assertFalse(hasattr(NoExpectMap, _expect_function_name(item)))

        for item in ITEM_DESCRIPTORS:
            self.assertTrue(hasattr(NoExpectMap, _with_function_name(item)))


class TestWith(unittest.TestCase):

    def test_with_msg_calls_with_self(self):
        """Check to make sure with_msg() uses self and not cls.

        At one point, it was assigned wrapped in classmethod(), which means it gets bound to cls instead of self. This
        worked fine for 99% of cases, but would stop working if the inner function had a 'self' argument that it needed.

        Remember: getattr(cls,...) returns methods bound with "cls" as the first argument if they're decorated with
        classmethod, and bound to nothing otherwise. getattr(self,...) returns methods bound with "cls" if they're
        decorated with classmethod, and bound to "self" otherwise.
        """

        color_item = ItemColor(item_color="The color of a child's laugh")

        class TestWithMsg(ItemMap):
            def __init__(self):
                self.counter = 7

            def with_color(self, _i: ItemColor):
                self.counter += 1

        test_map = TestWithMsg()

        test_map.with_msg(ItemColor, color_item)
        test_map.handle_message(color_item.wrap())

        self.assertEqual(test_map.counter, 9)

    def test_simple_override(self):
        class TestItemMap(ItemMap):
            def __init__(self):
                self.color = None
                self.size = None
                self.name_and_number = None

            def with_size(self, i: ItemSize):
                self.size = i

            def with_color(self, i: ItemColor):
                self.color = i

            def with_name_and_number(self, i: ItemNameAndNumber):
                self.name_and_number = i

        test_map = TestItemMap()

        size_item = ItemSize(size_units="horsepower", item_size=-3)
        color_item = ItemColor(item_color="Sorrow")
        name_and_number_item = ItemNameAndNumber(item_name="Foobuzz", item_number=112)

        test_map.with_size(size_item)
        test_map.with_color(color_item)
        test_map.with_name_and_number(name_and_number_item)

        self.assertEqual(test_map.size, size_item)
        self.assertEqual(test_map.color, color_item)
        self.assertEqual(test_map.name_and_number, name_and_number_item)

    def test_override_from_decorator(self):
        """Override with directly, instead of from a class that inherits from a decorated class."""

        @message_map(message_name="Item", message_types=ITEM_DESCRIPTORS)
        class TestItemMap(MessageMapTypeHints):
            def __init__(self):
                self.color = None
                self.size = None
                self.name_and_number = None

            def with_size(self, i: ItemSize):
                self.size = i

            def with_color(self, i: ItemColor):
                self.color = i

            def with_name_and_number(self, i: ItemNameAndNumber):
                self.name_and_number = i

        test_map = TestItemMap()

        size_item = ItemSize(size_units="horsepower", item_size=-3)
        color_item = ItemColor(item_color="Sorrow")
        name_and_number_item = ItemNameAndNumber(item_name="Foobuzz", item_number=112)

        test_map.with_size(size_item)
        test_map.with_color(color_item)
        test_map.with_name_and_number(name_and_number_item)

        self.assertEqual(test_map.size, size_item)
        self.assertEqual(test_map.color, color_item)
        self.assertEqual(test_map.name_and_number, name_and_number_item)

    def test_with_defined_in_decorator(self):
        class TestContainer:
            def __init__(self):
                self.color = None
                self.size = None
                self.name_and_number = None

        test_container = TestContainer()

        def with_size(i: ItemSize):
            test_container.size = i

        def with_color(i: ItemColor):
            test_container.color = i

        def with_name_and_number(i: ItemNameAndNumber):
            test_container.name_and_number = i

        @message_map(message_name="Item", message_types=ITEM_DESCRIPTORS,
                     with_functions={
                         ItemSize: with_size,
                         ItemColor: with_color,
                         ItemNameAndNumber: with_name_and_number
                     })
        class TestWithInDecorator(MessageMapTypeHints):
            pass

        test_map = TestWithInDecorator()

        size_item = ItemSize(size_units="horsepower", item_size=-3)
        color_item = ItemColor(item_color="Sorrow")
        name_and_number_item = ItemNameAndNumber(item_name="Foobuzz", item_number=112)

        test_map.with_size(size_item)
        test_map.with_color(color_item)
        test_map.with_name_and_number(name_and_number_item)

        self.assertEqual(test_container.size, size_item)
        self.assertEqual(test_container.color, color_item)
        self.assertEqual(test_container.name_and_number, name_and_number_item)

    def test_default_function(self):
        collected = []

        def collect(item: MessageCls):
            collected.append(item)

        @message_map(message_name="Item", message_types=ITEM_DESCRIPTORS,
                     default_handler=collect)
        class TestWithInDecorator(MessageMapTypeHints):
            pass

        test_map = TestWithInDecorator()

        size_item = ItemSize(size_units="horsepower", item_size=-3)
        color_item = ItemColor(item_color="Sorrow")
        name_and_number_item = ItemNameAndNumber(item_name="Foobuzz", item_number=112)

        test_map.with_size(size_item)
        test_map.with_color(color_item)
        test_map.with_name_and_number(name_and_number_item)

        self.assertListEqual(collected, [size_item, color_item, name_and_number_item])


class TestMessages(unittest.TestCase):
    def test_idempotent_wrap(self):
        i = ItemColor(item_color="gray")
        wrapped = Message(message_name=ItemColor.MESSAGE_NAME, payload=i)

        self.assertEqual(i.wrap(), wrapped)
        self.assertEqual(wrapped.wrap(), wrapped)

    def test_idempotent_unwrap(self):
        i = ItemColor(item_color="grey")
        wrapped = Message(message_name=ItemColor.MESSAGE_NAME, payload=i)

        self.assertEqual(wrapped.unwrap(ItemColor), i)
        self.assertEqual(i.unwrap(ItemColor), i)

    def test_unwrap_json_dict(self):
        i = ItemColor(item_color="charlie-brown")
        wrapped_dict = Message(message_name=ItemColor.MESSAGE_NAME, payload=i.to_dict())
        wrapped_json = Message(message_name=ItemColor.MESSAGE_NAME, payload=i.to_json())

        self.assertEqual(wrapped_dict.unwrap(ItemColor), i)
        self.assertEqual(wrapped_json.unwrap(ItemColor), i)

    def test_unwrap_wrong_type(self):
        i = ItemColor(item_color="cherry-noble")
        wrapped = Message(message_name=ItemColor.MESSAGE_NAME, payload=i)

        with self.assertRaises(TypeError):
            wrapped.unwrap(ItemSize)
        with self.assertRaises(TypeError):
            i.unwrap(ItemSize)


class TestMessageMapTypeHints(unittest.TestCase):
    def test_not_implemented_errors(self):
        class UninitializedClass(MessageMapTypeHints):
            pass

        with self.assertRaises(NotImplementedError) as e1:
            UninitializedClass().handle_message(None)
        with self.assertRaises(NotImplementedError) as e2:
            UninitializedClass().with_msg(None, None)
        with self.assertRaises(NotImplementedError) as e3:
            UninitializedClass().expect(None, None)

        expected_error = "Make sure UninitializedClass uses the @message_map decorator from the 'messages' package"
        self.assertRegex(str(e1.exception), expected_error)
        self.assertRegex(str(e2.exception), expected_error)
        self.assertRegex(str(e3.exception), expected_error)


if __name__ == '__main__':
    absltest.main()
