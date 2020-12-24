"""
#################################
# HERE THAR BE METAPROGRAMMINGS #
#################################

This library implements some metaprogramming magic to fill out classes decorated with the @message_map decorator.

See that decorator for the interface it provides classes. In short: it creates a message routing system

#########################################################
############ GLOSSARY AND NAMING CONVENTIONS ############
#########################################################
Dealing with the metaprogramming garbage and type shenanigans pulled in this file is complicated and annoying. To make
life easier, try to adhere to the following naming conventions (note: this file is not perfect)

  * "message": A Message instance, containing a MessageCls in the 'payload' field
  * "message_cls": Used for client-facing Type[MessageCls] varibles.
  * "message_c": Refers to a MessageCls instance
  * "message_t": Refers to a MessageCls type
  * "message_ti": Refers to a list of MessageClass types ("_TypeInstance")
  * "this_*": Refers to an instance of a message or event in a sub- or helper-function. Useful
    to avoid shadowing outer variables
  * "msg*": Same as "message*". Not allowed as function arguments.

Some of these distinguish between "client" and "internal" code. Prefer descriptive, full names on public methods and
classes - e.g. names you wouldn't have to read these comments to understand.

#####################################
############ STYLE RULES ############
#####################################
Metaprogramming garbage is difficult and annoying. Please adhere to the following rules wherever possible in
metaprogramming sections (e.g. the "EventTypeMap" and "CommandTypeMap" classes below, and the things initializing them)

  * DO NOT shadow outer variables
  * AVOID modifying variables inside a code block. Ex: a = 2; a = 3. Loop variables are obviously OK
  * PREFER moving complicated loop bodies into separate functions
  * AVOID using scope capture or closures in the middle of functions. Instead:
  * PREFER to put closures or similar functions inside narrowly-scoped outer functions
  * DO include type information in variable names
  * DO try to maintain type information, and keep it as tight as possible
  * DO name variables so it's obvious what type they contain by the name
"""
from dataclasses import dataclass
from typing import Type, Callable, Iterable, Optional, Any, List, Dict, TypeVar, Generic, cast

from dataclasses_json import dataclass_json
from dataclasses_jsonschema import JsonSchemaMixin

from commandserver.server_exceptions import UnsupportedMessageType
from common.utils import class_name

T = TypeVar('T')


@dataclass_json
class MessageCls(JsonSchemaMixin):
    """Represents a Payload for a Message, defined below. I.E. it contains all the fun data bits.

    Subclasses should describe all type information they care about for parsing and serializing using type annotations.
    Ex:
      server_code: Optional[int]
      message: Optional[str]

    As a reminder, messages should prefer optional for all fields - it makes it easier to switch between implementations
    and schemas moving forward. Throw a ValueError or something if a field is missing that you logically need.

    Attributes:
        MessageCls.MESSAGE_NAME: should be defined on all subclasses intending to see real, direct use. This is a short
        descriptor used by both humans and machines when doing things like reporting errors, disambiguating types,
        creating function names, etc - so keep it short and descriptive, no more than ~2 words.
    """
    MESSAGE_NAME: str

    def wrap(self) -> "Message":
        """Convert to a Message class.

        This is idempotent - self.wrap().wrap() will return the same thing as self.wrap().
        """
        return Message(message_name=self.MESSAGE_NAME, payload=self)

    def unwrap(self, message_class_type: Type["Types.M_C"]) -> "Types.M_C":
        if not isinstance(self, message_class_type):
            raise TypeError("Invalid type, message '%s' is not type '%s'" % (self, class_name(message_class_type)))

        return cast(Types.M_C, self)


@dataclass_json
@dataclass
class Message(JsonSchemaMixin):
    """Contains a wrapped MessageCls, including naming information.

    Payload is typically stored in an unprocessed state, because the "dataclass_json" library is bad at dealing with
    type ambiguity. Call "unwrap" with the type indicated by the 'message_name' field to get the appropriate message
    (or, more commonly, use a @message_map annotated class with handle_message(...) to route the message to a function
    that can handle it).

    Attributes:
        message_name: Name of the message, as defined in MessageCls.MESSAGE_NAME
        payload: The meat of the message. Use 'unwrap()' to get this in a programmer-friendly format.
    """
    message_name: Optional[str]

    # We leave this as an untyped Optional so dataclass_json doesn't jump the gun - but it's really a MessageCls.
    # It's expected that a class annotated by message_map() implements parsing.
    payload: Optional[Any]

    def wrap(self) -> "Message":
        """Returns a Message class. Idempotent version of MessageCls.wrap()."""
        return self

    def unwrap(self, message_class_type: Type["Types.M_C"]) -> "Types.M_C":
        """Returns the unwrapped message. This is idempotent: m.unwrap(t).unwrap(t) == m.unwrap(t).

        Message.payload may be a string, dict, or concrete class depending on how it was constructed. This class
        will disambiguate and parse the internal representation out into something useful to the caller.

        Args:
             message_class_type: The type of class to
        """

        # Rename to internal naming pattern.
        message_t: Type[MessageCls] = message_class_type
        if not isinstance(message_t, type):
            raise TypeError("Expected type as input, got %s" % (class_name(message_t),))
        if self.message_name != message_t.MESSAGE_NAME:
            raise TypeError("Invalid type, message '%s' is not type '%s'" % (self, class_name(message_t)))

        # Some class types are parameterless - we'll assume that to be the case here.
        if self.payload is None:
            return cast(Types.M_C, message_t())

        if isinstance(self.payload, dict):
            return cast(Types.M_C, message_t.from_dict(self.payload))
        if isinstance(self.payload, str):
            return cast(Types.M_C, message_t.from_json(self.payload))
        if isinstance(self.payload, message_t):
            return cast(Types.M_C, self.payload)
        raise TypeError(
            "Invalid type, message '%s' is not type '%s', or a supported sub-type" % (
                class_name(self.payload), class_name(message_t)))


class Types:
    """Contains some function types to make type annotation easier.

    Attributes:
        Types.M_C: Generic type variable for MessageCls in MessageMap functions and similar. Stands for "MessageClass"
        Types.M_T: Generic type variable for Messages in MessageMap functions and similar. Stands for "Message Type"
        Types.MessageHandler: The type of a function which accepts a MessageCls, and returns something. Used in @message_map
        classes for functions that replace "with_*" functions, as well as the default_hander function, and
        inputs to generated "expect_*(...)" functions.
        Types.T_MAP: Stand in for classes which extend MessageMapTypeHints and are decorated by @message_map. Stands for
        "Type Map".
    """
    M_C = TypeVar('M_C', bound=MessageCls)
    M_T = TypeVar('M_T', bound=Message)

    MessageHandler = Callable[["Types.M_C"], Any]

    # Represents the type returned by @message_map()
    T_MAP = TypeVar('T_MAP', bound="MessageMapTypeHints")


##########################
#   Utility Functions    #
##########################


def _with_function_name(message_t: Type[MessageCls]) -> str:
    """Returns the appropriate 'with' function name of message_t. ex: 'with_toggle_play(t: TogglePlayCommand)"""
    return "with_%s" % (message_t.MESSAGE_NAME.lower(),)


def _expect_function_name(message_t: Type[MessageCls]) -> str:
    """Returns the appropriate 'expect' fn name of message_t. Ex: 'expect_toggle_play(mh: Types.MessageHandler)'"""
    return "expect_%s" % (message_t.MESSAGE_NAME.lower())


def _expect(cls: "Types.T_MAP", message_t: Type[Types.M_C], message_handler: Types.MessageHandler):
    """Returns a TypeMap for the given message type by calling the resolved function for the type.

    ex: If you call "expect(PlayStateEvent, lambda x: ...)" this is equivalent to calling
    "expect_play_state(lambda x: ...)".

    Useful for testing, esp. on parameterized tests.
    """
    if not message_t or message_t not in cls.message_types:
        raise TypeError("Expected type in '%s', got '%s'" % (", ".join([class_name(m_t) for m_t in cls.message_types]),
                                                             class_name(message_t)))

    expect_cls_func = getattr(cls, _expect_function_name(message_t))
    return expect_cls_func(message_handler)


def _no_expect(_cls: "Types.T_MAP", *_argv, **_kwargs):
    """Assigned to classes which turned off the 'build_expect' flags.

    This happens when building a class from an expect function. It may also happen other times, I dunno.
    """
    raise NotImplementedError("Class does not support 'expect' methods.")


def _with_msg(self, message_t: Type[Types.M_C], message_c: Types.M_C):
    """Like calling with_.* directly for the given message_t.

    NOTE: 'with' is a python reserved keyword, so prefer assigning to 'with_msg()'.
    """
    with_cls_func = getattr(self, _with_function_name(message_t))
    return with_cls_func(message_c)


def _resolve_message_type(cls: "MessageMapTypeHints", message: Message) -> Type[Types.M_C]:
    """Resolves the MessageCls type of the input message."""
    message_t = next((message_t for message_t in cls.message_types
                      if message.message_name == message_t.MESSAGE_NAME), None)

    if not message_t:
        # We couldn't find the type "Message.MESSAGE_NAME" in cls.message_types, which denotes
        # the supported MessageCls types of that class.
        raise UnsupportedMessageType(
            routing_cls=cls, message_name=cls.message_name,
            message=message, expected_message_ti=cls.message_types)
    return message_t


def _handle_message(cls, message: Types.M_T) -> Any:
    """Takes an input message,parses its payload, and calls the appropriate 'with_*' function on cls."""
    msg_t: Type[MessageCls] = _resolve_message_type(cls, message)

    parsed_message = message.unwrap(msg_t)
    return cls.with_msg(msg_t, parsed_message)


def _build_expect_function(_cls: Type[Types.T_MAP],
                           message_name: str, message_t: Type[Types.M_C],
                           all_message_ti: List[Type[Types.M_C]]):
    """Returns the expect function for the given message_t.

    Args:
        _cls: The class type for which the expect function is being built for
        message_name: Name of the message class. Ex: "Event", "Command", "Message"
        message_t: Type of MessageCls for which the expect function should be built.
        all_message_ti: The list of all message types to be supported by _cls. Used to build "with" functions
        that throw Value errors.
    """

    def build_expect_message_class(passthrough_call: Types.MessageHandler) -> MessageMapTypeHints:
        if not callable(passthrough_call):
            raise TypeError("Expected input fn to be callable. Got '%s'" % (passthrough_call,))

        def bad_message(e: Type[Types.M_C]):
            raise ValueError(
                "Did not expect %s type '%s'" % (message_name, e.MESSAGE_NAME))

        def _passthrough(message_c: Types.M_C):
            return passthrough_call(message_c)

        @message_map(message_types=all_message_ti, build_expect=False,
                     message_name=_cls.message_name,
                     default_handler=bad_message,
                     with_functions={message_t: _passthrough})
        class ExpectMessageCls(MessageMapTypeHints):
            pass

        # Make sure to instantiate the class before returning it, because the end client wants a fully-functional
        # instance of a _cls SubClass, not the prototype subclass itself.
        return ExpectMessageCls()

    return build_expect_message_class


def _build_with_func(message_t: Type[Types.M_C]):
    def with_message(self, _2: Type[Types.M_C]):
        """The default 'with_<message_name>' function assigned to classes."""
        raise NotImplementedError(
            "%s '%s' not implemented or expected on the server" % (
                self.message_name.capitalize(), message_t.MESSAGE_NAME))

    return with_message


#############################
#  End Utility Functions    #
#############################

def message_map(message_name: str = "message",
                message_types: Iterable[Type[Types.M_C]] = None,
                build_expect=True,
                default_handler: Types.MessageHandler = None,
                with_functions: Dict[Type[Types.M_C], Types.MessageHandler] = None):
    """Supplies the annotated class with the ability to handle and route messages, as well as some utility functions

    Must extend MessageMapTypeHints. Primarily for IDE type hints, but also to make type checking happy. It's not
    perfect, but it's better than nothing.

    Classes annotated by this function receive the following additions:

        message_name: str
        message_types: List[Type[T]]

        def with_<message_name>(self, message: <MessageClass>) -> Any:
           # Handles <message_name>. Called by handle_message(...)
           pass

        def handle_message(self, message: Message):
           # Calls the with_* method corresponding to 'message.message_name'. It'll also parse the payload as the
           # appropriate subclass if necessary.

        @classmethod
        def expect_<message_name>(self, message_handler: Types.MessageHandler) -> Type[type(self)]:
          # Returns a message map populated with a single handler for the type indicated by <message_name>.
          # Ex: "EventTypeMap.expect_play_state(lambda ps_event: print(ps_event)).handle_message(ps_event)
          # which would print 'ps_event'.
          #
          # Useful for testing.

        @classmethod
        def expect(self, message_type: Type[MessageCls], message_handler: Types.MessageHandler) -> Type[type(self)]
          # The generic version of expect_<message_name>

        def with_msg(self, message_type: Type[MessageCls], message: MessageCls):
          # The generic version of with_<message_name>. Accepts MessageCls directly, unlike handle_message.

    args:
        message_name: The name of the message, for use in errors, debug messages, etc. Ex: "Event"
        message_types: The list of all message types this class should handle.
        build_expect: If false, expect_* functions will not be created. expect() will raise a "NotImplementedError".
        default_handler: If set, all with_* functions will use this function, instead of throwing a NotImplemented error
        with_functions: If set, the dictionary of types to functions will populate the definitions of the with_*
          functions
    """

    def wrap(cls):
        return _message_map(cls, message_name=message_name, message_types=message_types, build_expect=build_expect,
                            default_handler=default_handler, with_functions=with_functions)

    return wrap


def _message_map(cls,
                 message_name: str = "message",
                 message_types: List[Type[Types.M_C]] = None,
                 build_expect=True,
                 default_handler: Types.MessageHandler = None,
                 with_functions: Dict[Type[Types.M_C], Types.MessageHandler] = None):
    """Inner function for message_map.

    If you pass arguments to a decorator, you get the arguments but not the object you're decorating. So, you return
    a function that takes just one arg (which will be decorated object) and which captured all input arguments, and
    then call an inner function that actually does the work.
    """
    message_ti = list(message_types if message_types else [])
    cls.message_types = message_ti
    cls.message_name = message_name

    def wrap_classmethod(f: Types.MessageHandler):
        """Strip out "self" and "cls" from a function call before passing to a 'Types.MessageHandler' function."""

        def inner(_cls, *argv):
            return f(*argv)

        return inner

    default_func = classmethod(wrap_classmethod(default_handler)) if default_handler else None
    for msg_t in message_ti:
        with_func_name = _with_function_name(msg_t)
        if not hasattr(cls, with_func_name):
            setattr(cls, with_func_name,
                    default_func if default_handler else _build_with_func(message_t=msg_t))

    if with_functions:
        for msg_t, with_function in with_functions.items():
            with_func_name = _with_function_name(msg_t)
            setattr(cls, with_func_name, classmethod(wrap_classmethod(with_function)))
    cls.with_msg = _with_msg
    cls.handle_message = _handle_message

    if build_expect:
        for msg_t in message_ti:
            expect_func_name = _expect_function_name(msg_t)
            if not hasattr(cls, expect_func_name):
                setattr(cls, expect_func_name, _build_expect_function(cls, message_name=message_name,
                                                                      message_t=msg_t,
                                                                      all_message_ti=message_ti))

        cls.expect = classmethod(_expect)
    else:
        cls.expect = classmethod(_no_expect)

    return cls


class MessageMapTypeHints(Generic[Types.M_T, Types.M_C]):
    """Type hints for message handlers.

    PyCharm does not like decorators adding new fields on to objects, so in order to tell it (and potentially MyPy) what
    is available, it's recommended you subtype this class on all classes decorated with @message_handler.
    """

    # Message types supported by this handler.
    message_types: Iterable[Type[Types.M_C]]

    # The name of the message to use in error messages, etc.
    message_name: str

    _NOT_IMPLEMENTED_ERROR_MSG = "Make sure %s uses the @message_map decorator from the 'messages' package"

    def handle_message(self, message: Types.M_T):
        """Handles a message by calling the method corresponding to it's type."""
        raise NotImplementedError(MessageMapTypeHints._NOT_IMPLEMENTED_ERROR_MSG % (class_name(self),))

    def with_msg(self, message_cls: Type[Types.M_C], message: Types.M_C):
        """Similar to calling 'with_*()' directly. Accepts a MessageCls instead of Message like 'handle_message'."""
        raise NotImplementedError(MessageMapTypeHints._NOT_IMPLEMENTED_ERROR_MSG % (class_name(self),))

    @classmethod
    def expect(cls, message_cls: Type[Types.M_C], handler: Types.MessageHandler) -> Types.T_MAP:
        raise NotImplementedError(MessageMapTypeHints._NOT_IMPLEMENTED_ERROR_MSG % (class_name(cls),))
