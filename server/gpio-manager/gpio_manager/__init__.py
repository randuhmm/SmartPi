# -*- coding: utf-8 -*-
"""Raspberry PI GPIO Manager"""
from __future__ import absolute_import, print_function, unicode_literals

import os
import signal
import sys

from collections import namedtuple
from importlib import import_module
from vine.utils import wraps


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

    def setup(*args):
        print(args)

    def input(*args):
        pass

    def output(*args):
        pass


if os.name == 'nt':
    GPIO = WindowsGPIO()
elif 'posix':
    import GPIO.GPIO as GPIO


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
        print(args)
        self._conf = None
        self._setup_funcs = []
        self.GPIO = GPIO
        self._tasks = {}

    def config_from_object(self, obj):
        self._config_source = obj

    def _load_config(self):
        s = self._config_source.split(':')
        if len(s) == 2:
            self._conf = getattr(import_module(s[0]), s[1])
        else:
            self._conf = import_module(s[0])
        return self._conf

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

    def do(self, *args, **opts):
        def inner_create_task_cls(shared=True, filter=None, lazy=True, **opts):

            def _create_task_cls(fun):
                # ret = PromiseProxy(self._task_from_fun, (fun,), opts,
                #                    __doc__=fun.__doc__)
                # self._pending.append(ret)
                ret = type(fun.__name__, (MyTask,), dict({
                    'app': self,
                    'name': self.gen_task_name(fun.__name__, fun.__module__),
                    'run': staticmethod(fun),
                    '_decorated': True,
                    '__doc__': fun.__doc__,
                    '__module__': fun.__module__,
                    '__wrapped__': staticmethod(fun)}, **opts))()
                return ret

            return _create_task_cls

        if len(args) == 1:
            if callable(args[0]):
                return inner_create_task_cls(**opts)(*args)
            raise TypeError('argument 1 to @task() must be a callable')
        if args:
            raise TypeError(
                '@task() takes exactly 1 argument ({0} given)'.format(
                    sum([len(args), len(opts)])))
        return inner_create_task_cls(**opts)

    def gen_task_name(self, name, module):
        return gen_task_name(self, name, module)

    def run(self):

        # setup gpio
        for setup_func in self._setup_funcs:
            setup_func(self)

        running = True
        with GracefulInterruptHandler() as h:
            print('Enter "q" to Quit')
            while running:
                q = raw_input()
                if h.interrupted or q == 'q':
                    running = False
                    print('Exiting')


class MyTask(object):
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

__module__ = __name__  # used by Proxy class body

PY3 = sys.version_info[0] == 3

from .five import bytes_if_py2, string


def _default_cls_attr(name, type_, cls_value):
    # Proxy uses properties to forward the standard
    # class attributes __module__, __name__ and __doc__ to the real
    # object, but these needs to be a string when accessed from
    # the Proxy class directly.  This is a hack to make that work.
    # -- See Issue #1087.

    def __new__(cls, getter):
        instance = type_.__new__(cls, cls_value)
        instance.__getter = getter
        return instance

    def __get__(self, obj, cls=None):
        return self.__getter(obj) if obj is not None else self

    return type(bytes_if_py2(name), (type_,), {
        '__new__': __new__, '__get__': __get__,
    })


def try_import(module, default=None):
    """Try to import and return module, or return
    None if the module does not exist."""
    try:
        return import_module(module)
    except ImportError:
        return default


class Proxy(object):
    """Proxy to another object."""

    # Code stolen from werkzeug.local.Proxy.
    __slots__ = ('__local', '__args', '__kwargs', '__dict__')

    def __init__(self, local,
                 args=None, kwargs=None, name=None, __doc__=None):
        object.__setattr__(self, '_Proxy__local', local)
        object.__setattr__(self, '_Proxy__args', args or ())
        object.__setattr__(self, '_Proxy__kwargs', kwargs or {})
        if name is not None:
            object.__setattr__(self, '__custom_name__', name)
        if __doc__ is not None:
            object.__setattr__(self, '__doc__', __doc__)

    @_default_cls_attr('name', str, __name__)
    def __name__(self):
        try:
            return self.__custom_name__
        except AttributeError:
            return self._get_current_object().__name__

    @_default_cls_attr('qualname', str, __name__)
    def __qualname__(self):
        try:
            return self.__custom_name__
        except AttributeError:
            return self._get_current_object().__qualname__

    @_default_cls_attr('module', str, __module__)
    def __module__(self):
        return self._get_current_object().__module__

    @_default_cls_attr('doc', str, __doc__)
    def __doc__(self):
        return self._get_current_object().__doc__

    def _get_class(self):
        return self._get_current_object().__class__

    @property
    def __class__(self):
        return self._get_class()

    def _get_current_object(self):
        """Return the current object.  This is useful if you want the real
        object behind the proxy at a time for performance reasons or because
        you want to pass the object into a different context.
        """
        loc = object.__getattribute__(self, '_Proxy__local')
        if not hasattr(loc, '__release_local__'):
            return loc(*self.__args, **self.__kwargs)
        try:  # pragma: no cover
            # not sure what this is about
            return getattr(loc, self.__name__)
        except AttributeError:  # pragma: no cover
            raise RuntimeError('no object bound to {0.__name__}'.format(self))

    @property
    def __dict__(self):
        try:
            return self._get_current_object().__dict__
        except RuntimeError:  # pragma: no cover
            raise AttributeError('__dict__')

    def __repr__(self):
        try:
            obj = self._get_current_object()
        except RuntimeError:  # pragma: no cover
            return '<{0} unbound>'.format(self.__class__.__name__)
        return repr(obj)

    def __bool__(self):
        try:
            return bool(self._get_current_object())
        except RuntimeError:  # pragma: no cover
            return False
    __nonzero__ = __bool__  # Py2

    def __dir__(self):
        try:
            return dir(self._get_current_object())
        except RuntimeError:  # pragma: no cover
            return []

    def __getattr__(self, name):
        if name == '__members__':
            return dir(self._get_current_object())
        return getattr(self._get_current_object(), name)

    def __setitem__(self, key, value):
        self._get_current_object()[key] = value

    def __delitem__(self, key):
        del self._get_current_object()[key]

    def __setslice__(self, i, j, seq):
        self._get_current_object()[i:j] = seq

    def __delslice__(self, i, j):
        del self._get_current_object()[i:j]

    def __setattr__(self, name, value):
        setattr(self._get_current_object(), name, value)

    def __delattr__(self, name):
        delattr(self._get_current_object(), name)

    def __str__(self):
        return str(self._get_current_object())

    def __lt__(self, other):
        return self._get_current_object() < other

    def __le__(self, other):
        return self._get_current_object() <= other

    def __eq__(self, other):
        return self._get_current_object() == other

    def __ne__(self, other):
        return self._get_current_object() != other

    def __gt__(self, other):
        return self._get_current_object() > other

    def __ge__(self, other):
        return self._get_current_object() >= other

    def __hash__(self):
        return hash(self._get_current_object())

    def __call__(self, *a, **kw):
        return self._get_current_object()(*a, **kw)

    def __len__(self):
        return len(self._get_current_object())

    def __getitem__(self, i):
        return self._get_current_object()[i]

    def __iter__(self):
        return iter(self._get_current_object())

    def __contains__(self, i):
        return i in self._get_current_object()

    def __getslice__(self, i, j):
        return self._get_current_object()[i:j]

    def __add__(self, other):
        return self._get_current_object() + other

    def __sub__(self, other):
        return self._get_current_object() - other

    def __mul__(self, other):
        return self._get_current_object() * other

    def __floordiv__(self, other):
        return self._get_current_object() // other

    def __mod__(self, other):
        return self._get_current_object() % other

    def __divmod__(self, other):
        return self._get_current_object().__divmod__(other)

    def __pow__(self, other):
        return self._get_current_object() ** other

    def __lshift__(self, other):
        return self._get_current_object() << other

    def __rshift__(self, other):
        return self._get_current_object() >> other

    def __and__(self, other):
        return self._get_current_object() & other

    def __xor__(self, other):
        return self._get_current_object() ^ other

    def __or__(self, other):
        return self._get_current_object() | other

    def __div__(self, other):
        return self._get_current_object().__div__(other)

    def __truediv__(self, other):
        return self._get_current_object().__truediv__(other)

    def __neg__(self):
        return -(self._get_current_object())

    def __pos__(self):
        return +(self._get_current_object())

    def __abs__(self):
        return abs(self._get_current_object())

    def __invert__(self):
        return ~(self._get_current_object())

    def __complex__(self):
        return complex(self._get_current_object())

    def __int__(self):
        return int(self._get_current_object())

    def __float__(self):
        return float(self._get_current_object())

    def __oct__(self):
        return oct(self._get_current_object())

    def __hex__(self):
        return hex(self._get_current_object())

    def __index__(self):
        return self._get_current_object().__index__()

    def __coerce__(self, other):
        return self._get_current_object().__coerce__(other)

    def __enter__(self):
        return self._get_current_object().__enter__()

    def __exit__(self, *a, **kw):
        return self._get_current_object().__exit__(*a, **kw)

    def __reduce__(self):
        return self._get_current_object().__reduce__()

    if not PY3:  # pragma: no cover
        def __cmp__(self, other):
            return cmp(self._get_current_object(), other)  # noqa

        def __long__(self):
            return long(self._get_current_object())  # noqa

        def __unicode__(self):
            try:
                return string(self._get_current_object())
            except RuntimeError:  # pragma: no cover
                return repr(self)


class PromiseProxy(Proxy):
    """This is a proxy to an object that has not yet been evaulated.
    :class:`Proxy` will evaluate the object each time, while the
    promise will only evaluate it once.
    """

    __slots__ = ('__pending__',)

    def _get_current_object(self):
        try:
            return object.__getattribute__(self, '__thing')
        except AttributeError:
            return self.__evaluate__()

    def __then__(self, fun, *args, **kwargs):
        if self.__evaluated__():
            return fun(*args, **kwargs)
        from collections import deque
        try:
            pending = object.__getattribute__(self, '__pending__')
        except AttributeError:
            pending = None
        if pending is None:
            pending = deque()
            object.__setattr__(self, '__pending__', pending)
        pending.append((fun, args, kwargs))

    def __evaluated__(self):
        try:
            object.__getattribute__(self, '__thing')
        except AttributeError:
            return False
        return True

    def __maybe_evaluate__(self):
        return self._get_current_object()

    def __evaluate__(self,
                     _clean=('_Proxy__local',
                             '_Proxy__args',
                             '_Proxy__kwargs')):
        try:
            thing = Proxy._get_current_object(self)
        except:
            raise
        else:
            object.__setattr__(self, '__thing', thing)
            for attr in _clean:
                try:
                    object.__delattr__(self, attr)
                except AttributeError:  # pragma: no cover
                    # May mask errors so ignore
                    pass
            try:
                pending = object.__getattribute__(self, '__pending__')
            except AttributeError:
                pass
            else:
                try:
                    while pending:
                        fun, args, kwargs = pending.popleft()
                        fun(*args, **kwargs)
                finally:
                    try:
                        object.__delattr__(self, '__pending__')
                    except AttributeError:  # pragma: no cover
                        pass
            return thing

