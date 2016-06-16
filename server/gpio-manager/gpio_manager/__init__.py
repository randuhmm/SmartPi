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
import django

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

    BOARD = None
    BCM = None
    IN = None
    OUT = None
    RISING = None
    FALLING = None
    HIGH = None
    LOW = None
    PUD_DOWN = None
    PUD_UP = None
    BOTH = None

    def setup(*args, **kwargs):
        pass

    def setmode(*args, **kwargs):
        pass

    def input(*args, **kwargs):
        pass

    def output(*args, **kwargs):
        pass

    def add_event_detect(*args, **kwargs):
        pass

    def remove_event_detect(*args, **kwargs):
        pass

    def cleanup(*args, **kwargs):
        pass


if os.name == 'nt':
    GPIO = WindowsGPIO()
    BaseServer = SocketServer.TCPServer
elif 'posix':
    import RPi.GPIO as GPIO
    BaseServer = SocketServer.UnixStreamServer


class GpioRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        encoding, encoded_size, encoded_data = self.data.split(':')
        encoded_size = int(encoded_size)
        while encoded_size > len(encoded_data):
            encoded_data += self.request.recv(1024).strip()

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


def shared_init(*args, **opts):
    app = GpioManager.get_current_app()
    return app.init(*args, **opts)


def shared_command(*args, **opts):
    app = GpioManager.get_current_app()
    return app.command(*args, **opts)


class GpioManager(object):

    _apps = []

    def __init__(self, *args):
        self._GPIO = GPIO
        self._conf = None
        self._init_funcs = {}
        self._command_funcs = {}
        self._input_handlers = {}
        GpioManager._apps.append(self)

        # Setup django
        django.setup()

    def __del__(self):
        GpioManager._apps.remove(self)

    @staticmethod
    def get_current_app():
        return GpioManager._apps[0]

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

    def get_command_by_name(self, name):
        return self._command_funcs[name]

    def init(self, *args, **opts):
        return self.create_func(Init, self._init_funcs, *args, **opts)

    def command(self, *args, **opts):
        return self.create_func(Command, self._command_funcs, *args, **opts)

    def create_func(self, _class, _dict, *args, **opts):
        def create_func_cls(fun):
            name = self.gen_task_name(fun.__name__, fun.__module__)
            ret = type(fun.__name__, (_class,), dict({
                'app': self,
                'name': name,
                'run': fun}, **opts))()
            _dict[name] = ret
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

    def gpio_setup(self, *args, **kwargs):
        return self._GPIO.setup(*args, **kwargs)

    def gpio_output(self, *args, **kwargs):
        return self._GPIO.output(*args, **kwargs)

    def gpio_input(self, *args, **kwargs):
        return self._GPIO.input(*args, **kwargs)

    def gpio_cleanup(self, *args, **kwargs):
        return self._GPIO.cleanup(*args, **kwargs)

    def gpio_add_event_detect(self, gpio, edge, callback,
                              bouncetime=None):
        if callback is not None:
            fx = callback.run
        return self._GPIO.add_event_detect(gpio, edge, fx, bouncetime)

    def gpio_remove_event_detect(self, *args, **kwargs):
        return self._GPIO.remove_event_detect(*args, **kwargs)

    def run(self):

        django.setup()

        # setup gpio
        self.GPIO.setmode(self.GPIO.BOARD)
        for name, func in self._init_funcs.iteritems():
            func.run()

        # setup socket server
        if BaseServer == SocketServer.TCPServer:
            HOST, PORT = "localhost", 9999
            # Create the server, binding to localhost on port 9999
            server = GpioServer(self, (HOST, PORT), GpioRequestHandler)
            # Activate the server; this will keep running until you
            # interrupt the program with Ctrl-C
        elif BaseServer == SocketServer.UnixStreamServer:
            server_address = './gpio.sock'
            try:
                os.unlink(server_address)
            except OSError:
                if os.path.exists(server_address):
                    raise
            server = GpioServer(self, server_address, GpioRequestHandler)
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
                    self.GPIO.cleanup()
                    print('Exiting')

    def _load_config(self):
        s = self._config_source.split(':')
        if len(s) == 2:
            self._conf = getattr(import_module(s[0]), s[1])
        else:
            self._conf = import_module(s[0])
        return self._conf


class Init(object):
    pass


class Command(object):

    def apply(self, *args, **kwargs):

        command = {
            'id': 123,
            'type': 'command',
            'command': self.name,
            'args': args,
            'kwargs': kwargs,
        }
        encoded_command = base64.b64encode(pickle.dumps(command))
        data = 'pickle:%d:%s' % (len(encoded_command), encoded_command)

        try:
            # setup socket connection
            if BaseServer == SocketServer.TCPServer:
                HOST, PORT = 'localhost', 9999
                # Create a socket (SOCK_STREAM means a TCP socket)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((HOST, PORT))
            elif BaseServer == SocketServer.UnixStreamServer:
                server_address = './gpio.sock'
                # Create a socket (SOCK_STREAM means a TCP socket)
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(server_address)
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
            sock.close()


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
