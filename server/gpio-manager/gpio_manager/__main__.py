from __future__ import absolute_import, print_function, unicode_literals
from importlib import import_module

__all__ = ['main']


def main():
    app = getattr(import_module('project.gpio'), 'app')
    app.run()


if __name__ == '__main__':  # pragma: no cover
    main()
