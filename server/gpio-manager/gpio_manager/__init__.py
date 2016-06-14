# -*- coding: utf-8 -*-
"""Raspberry PI GPIO Manager"""
from __future__ import absolute_import, print_function, unicode_literals

import os
import signal
import sys
import socket
import SocketServer
import threading
import pickle
import base64

from collections import namedtuple
from importlib import import_module


version_info_t = namedtuple(
    'version_info_t', ('major', 'minor', 'micro', 'releaselevel', 'serial'),
)

SERIES = '0today8'
VERSION = version_info = version_info_t(0, 1, 0, 'rc2', '')

__version__ = '{0.major}.{0.minor}.{0.micro}{0.releaselevel}'.format(VERSION)
__author__ = 'Jonny Morrill'
__contact__ = 'jonny@morrill.me'
__homepage__ = 'http://'
__docformat__ = 'restructuredtext'

# -eof meta-

__all__ = [
    'GpioManager', '__version__',
]

VERSION_BANNER = '{0} ({1})'.format(__version__, SERIES)


class WindowsGPIO(object):

    INPUT = None
    OUTPUT = None
    RISING = None
    FALLING = None
    HIGH = None
    LOW = None

    def setup(*args):
        print(args)

    def input(*args):
        pass

    def output(*args):
        pass

    def add_event_detect(*args):
        pass


if os.name == 'nt':
    GPIO = WindowsGPIO()
    BaseServer = SocketServer.TCPServer
elif 'posix':
    import GPIO.GPIO as GPIO
    BaseServer = SocketServer.UnixStreamServer


class GpioRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        encoding, encoded_data = self.data.split(':')
        if encoding == 'pickle':
            decoded_data = pickle.loads(base64.b64decode(encoded_data))
        elif encoding == 'json':
            # TODO:
            pass
        else:
            raise Exception()

        request_type = decoded_data['type']
        result = None
        if request_type == 'command':
            name = decoded_data['command']
            command = self.server.gpio_manager.get_command_by_name(name)
            args = decoded_data['args']
            kwargs = decoded_data['kwargs']
            result = command.run(*args, **kwargs)

        if encoding == 'pickle':
            response_data = base64.b64encode(pickle.dumps(result))
        self.request.sendall('%s:%s' % (encoding, response_data))


class GpioServer(BaseServer):

    def __init__(self, gpio_manager, *args, **kwargs):
        self.gpio_manager = gpio_manager
        BaseServer.__init__(self, *args, **kwargs)


MP_MAIN_FILE = os.environ.get('MP_MAIN_FILE')


def gen_task_name(app, name, module_name):
    """Generate task name from name/module pair."""
    module_name = module_name or '__main__'
    try:
        module = sys.modules[module_name]
    except KeyError:
        # Fix for manage.py shell_plus (Issue #366)
        module = None

    if module is not None:
        module_name = module.__name__
        # - If the task module is used as the __main__ script
        # - we need to rewrite the module part of the task name
        # - to match App.main.
        if MP_MAIN_FILE and module.__file__ == MP_MAIN_FILE:
            # - see comment about :envvar:`MP_MAIN_FILE` above.
            module_name = '__main__'
    if module_name == '__main__' and app.main:
        return '.'.join([app.main, name])
    return '.'.join(p for p in (module_name, name) if p)


class GpioManager(object):

    def __init__(self, *args):
        self._GPIO = GPIO
        self._conf = None
        self._setup_funcs = []
        self._commands = {}
        self._input_handlers = {}

    @property
    def GPIO(self):
        return self._GPIO

    def config_from_object(self, obj):
        self._config_source = obj

    def autodiscover(self):
        # TODO: autodiscover stuff...
        pass

    @property
    def conf(self):
        """Current configuration."""
        if self._conf is None:
            self._conf = self._load_config()
        return self._conf

    def setup(self, *args, **opts):
        self._setup_funcs.append(args[0])

    def command(self, *args, **opts):

        def create_func_cls(fun):
            name = self.gen_task_name(fun.__name__, fun.__module__)
            ret = type(fun.__name__, (Command,), dict({
                'app': self,
                'name': name,
                'run': fun}, **opts))()
            self._commands[name] = ret
            return ret

        if len(args) == 1:
            if callable(args[0]):
                return create_func_cls(*args)
            raise TypeError('argument 1 to @task() must be a callable')
        else:
            raise TypeError(
                '@task() takes exactly 1 argument ({0} given)'.format(
                    sum([len(args), len(opts)])))

    def get_command_by_name(self, name):
        return self._commands[name]

    def input_handler(self, *args, **opts):

        def create_func_cls(fun):
            name = self.gen_task_name(fun.__name__, fun.__module__)
            ret = type(fun.__name__, (InputHandler,), dict({
                'app': self,
                'name': name,
                'run': fun}, **opts))()
            self._input_handlers[name] = ret
            return ret

        if len(args) == 1:
            if callable(args[0]):
                return create_func_cls(*args)
            raise TypeError('argument 1 to @task() must be a callable')
        else:
            raise TypeError(
                '@task() takes exactly 1 argument ({0} given)'.format(
                    sum([len(args), len(opts)])))

    def gen_task_name(self, name, module):
        return gen_task_name(self, name, module)

    def gpio_setup(self, *args):
        return self._GPIO.setup(*args)

    def gpio_output(self, *args):
        return self._GPIO.output(*args)

    def gpio_input(self, *args):
        return self._GPIO.setup(*args)

    def gpio_add_event_detect(self, gpio, edge, callback=None,
                              bouncetime=None):
        if callback is not None:
            fx = callback.run
        return self._GPIO.add_event_detect(gpio, edge, fx, bouncetime)

    def run(self):

        # setup gpio
        for fun in self._setup_funcs:
            obj = type(fun.__name__, (Setup,), dict({
                'app': self,
                'name': self.gen_task_name(fun.__name__, fun.__module__),
                'run': fun},))()
            obj.run()

        # setup socket server
        if BaseServer == SocketServer.TCPServer:
            HOST, PORT = "localhost", 9999
            # Create the server, binding to localhost on port 9999
            server = GpioServer(self, (HOST, PORT), GpioRequestHandler)
            # Activate the server; this will keep running until you
            # interrupt the program with Ctrl-C
        elif BaseServer == SocketServer.UnixStreamServer:
            pass
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()

        running = True
        with GracefulInterruptHandler() as h:
            print('Enter "q" to Quit')
            while running:
                q = raw_input()
                if h.interrupted or q == 'q':
                    running = False
                    print('Exiting')

    def _load_config(self):
        s = self._config_source.split(':')
        if len(s) == 2:
            self._conf = getattr(import_module(s[0]), s[1])
        else:
            self._conf = import_module(s[0])
        return self._conf


class Setup(object):
    pass


class Command(object):

    def apply(self, *args, **kwargs):
        HOST, PORT = 'localhost', 9999
        command = {
            'id': 123,
            'type': 'command',
            'command': self.name,
            'args': args,
            'kwargs': kwargs,
        }
        data = 'pickle:%s' % base64.b64encode(pickle.dumps(command))

        # Create a socket (SOCK_STREAM means a TCP socket)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Connect to server and send data
            sock.connect((HOST, PORT))
            sock.sendall(data + '\n')

            # Receive data from the server and shut down
            received_data = sock.recv(1024)
            encoding, encoded_data = received_data.split(':')
            if encoding == 'pickle':
                return pickle.loads(base64.b64decode(encoded_data))
            elif encoding == 'json':
                # TODO:
                pass
            else:
                raise Exception()

        finally:
            print("CLOSING")
            sock.close()


class InputHandler(object):
    pass


class GracefulInterruptHandler(object):

    def __init__(self, sig=signal.SIGINT):
        self.sig = sig

    def __enter__(self):

        self.interrupted = False
        self.released = False

        self.original_handler = signal.getsignal(self.sig)

        def handler(signum, frame):
            self.release()
            self.interrupted = True

        signal.signal(self.sig, handler)

        return self

    def __exit__(self, type, value, tb):
        self.release()

    def release(self):

        if self.released:
            return False

        signal.signal(self.sig, self.original_handler)

        self.released = True

        return True
