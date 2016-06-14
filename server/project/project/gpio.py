from __future__ import absolute_import, unicode_literals

import os
import time

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
    self.app.gpio_setup(13, self.app.GPIO.IN,
                        pull_up_down=self.app.GPIO.PUD_DOWN)
    self.app.gpio_add_event_detect(13, app.GPIO.RISING,
                                   callback=handle_on,
                                   bouncetime=200)


@app.command
def turn_on(self, pin):
    print 'turn_on'
    ret = self.app.gpio_output(pin, self.app.GPIO.HIGH)
    import pdb; pdb.set_trace()
    return ret


@app.command
def turn_off(self, pin):
    print 'turn_off'
    return self.app.gpio_output(pin, self.app.GPIO.LOW)


@app.command
def get_input(self, pin):
    return self.app.gpio_input(pin)


@app.input_handler
def handle_on(self, channel):
    time.sleep(0.1)
    v = self.app.GPIO.input(channel)
    print 'handle_on %d' % v
