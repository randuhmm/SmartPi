from __future__ import absolute_import, unicode_literals

import os

from gpio_manager import GpioManager

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

from django.conf import settings  # noqa

app = GpioManager('project')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')

# load task modules from all registered Django app configs.
app.autodiscover()


@app.setup
def test_setup(app):
    app.GPIO.setup(13, app.GPIO.INPUT)


@app.do
def turnon(app, pin):
    print "on"
