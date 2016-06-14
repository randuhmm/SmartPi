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
def test_setup(self):
    self.app.gpio_setup(13, app.GPIO.OUTPUT)
    #self.app.gpio_add_event_detect(13, app.GPIO.RISING, handle_on)


@app.command
def turn_on(self, pin):
    print 'turn_on'
    return self.app.gpio_output(pin, app.GPIO.HIGH)


@app.command
def turn_off(self, pin):
    print 'turn_off'
    return self.app.gpio_output(pin, app.GPIO.LOW)


@app.input_handler
def handle_on(self, channel):
    import pdb; pdb.set_trace()
