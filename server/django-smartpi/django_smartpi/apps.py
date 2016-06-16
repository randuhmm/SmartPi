from __future__ import unicode_literals

from django.apps import AppConfig


class DjangoSmartpiConfig(AppConfig):
    name = 'django_smartpi'

    def ready(self):
        from django_smartpi import signals  # noqa
