"""
Implements a commandline console that supports some basic debugging and generic handling of input commands.

This is a bit more complicated than you might expect because the user will expect commands to be interpreted in a
non-blocking fashion, and because there are a lot of race conditions when you start doing stuff.json like that.

As a result,
"""

from __future__ import generators

import collections
import shlex
import sys
import threading
import time
from queue import Queue
from typing import Optional, Generator


def echo(argv):
    print(argv.join(" "))


Command = collections.namedtuple("Command", ("command", "arguments"), defaults=[list])


class ConsoleOutput(object):
    """Holds output from the console object."""

    def __init__(self, queue: Queue):
        self.queue = queue
        self.terminate = False

    def commands(self, timeout: Optional[float] = None) -> Generator[Command, None, None]:
        """Yields commands in a blocking fashion as a generator object."""
        while not self.terminate:
            c = self.queue.get(block=True, timeout=timeout)
            if c.command == "exit":
                return
            yield c
            self.queue.task_done()

    def add_command(self, command: Command):
        """Add a command to be processed"""
        self.queue.put(command)

    def join(self):
        """Wait for all inputs to finish processing."""
        self.queue.join()

    def close(self):
        """Append an "exit" to the end of the queue"""
        self.queue.put(Command(command="exit", arguments=[]))


class Console(object):
    """Represents a console.

    Non-blockingly puts lines of input into the queue when they're interpreted as commands.

    To use this, you create the object, then call "start()" to begin processing input. You can then call "write"
    to write messages to the user, while the "input" pipe passed in during __init__ will be continually monitored for
    commands from the user.
    """

    def __init__(self, console_input=sys.stdin, output=sys.stdout):
        self.output = output
        self.input = console_input
        self.console_output = ConsoleOutput(Queue())
        self.readline_output = Queue()

    def start(self) -> ConsoleOutput:
        """Begins processing input, returns a ConsoleOutput object, which contains all the post-processed output."""
        input_thread = threading.Thread(target=self._run, args=(self.console_output,))
        input_thread.daemon = True
        input_thread.start()

        return self.console_output

    def write(self, message):
        """Write a message to output to the user.."""
        self.output.write(message + "\n")
        self.output.flush()

    def close(self):
        """Force this console to terminate itself.

        This function has the courtesy to flush before leaving.
        """
        self.input.flush()
        # Super hacky, but: We're only working on a single logical thread. We need to give up control to
        # the event manager to ensure the flush above gets processed before putting "exit" on the queue
        # to avoid preempting anything =/
        time.sleep(.0025)
        self.console_output.queue.put(Command(command="exit", arguments=[]))

    def process_readline(self, console_out: ConsoleOutput):
        """Process all currently queued inputs.

        This reads from readline_output, which allows for backchannel input buffering (e.g. queuing inputs manually
        through readline_output instead of having the user do it through stdin)
        """
        while not self.readline_output.empty():
            console_input = self.readline_output.get()

            # User didn't enter anything meaningful...
            if not console_input.strip():
                continue

            values = shlex.split(console_input, comments=False, posix=True)
            command = Command(command=values[0], arguments=values[1:])
            console_out.add_command(command)

    def _run(self, console_out: ConsoleOutput):
        """Continually write command prompts and read input commands from the commandline.

        Called by the thread manager in "start()", should not be called more than once during a program's runtime for
        a given "input" and "output" - not just a given "console" object.
        """
        while True:
            self.output.write(">>> ")
            self.output.flush()
            self.readline_output.put(self.input.readline())
            self.process_readline(console_out)
            console_out.join()
