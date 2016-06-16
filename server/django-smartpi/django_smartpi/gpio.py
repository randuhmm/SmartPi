from gpio_manager import shared_init, shared_command
from django.core.exceptions import ObjectDoesNotExist
import time

from django_smartpi.models import GpioDevice, GpioPin


@shared_init
def gpio_init(self):
    subclasses = GpioDevice.__class__.__subclasses__(GpioDevice)
    for subclass in subclasses:
        for obj in subclass.objects.all():
            obj.gpio_init(self.app)


@shared_command
def gpio_add_device(self, device):
    print 'adding device'
    device.gpio_init(self.app)


@shared_command
def gpio_delete_device(self, device):
    print 'deleteing device'
    device.gpio_reset(self.app)


@shared_command
def gpio_update_device(self, device):
    print 'updating device'
    device.gpio_reset(self.app)
    device.gpio_init(self.app)


@shared_command
def gpio_setup(self, pin, mode, **kwargs):
    self.app.gpio_setup(pin, mode, **kwargs)


@shared_command
def gpio_cleanup(self, *args):
    return self.app.gpio_cleanup(*args)


@shared_command
def gpio_output(self, pin, value):
    print '%d %d' % (pin, value)
    self.app.gpio_output(pin, value)


@shared_command
def gpio_input(self, pin):
    try:
        device = GpioPin.objects.get(
            pin_number=pin).gpiodevicepin.gpioinputdevice
    except ObjectDoesNotExist:
        return
    device.gpio_input(self.app)


@shared_command
def handle_on(self, channel):
    time.sleep(0.2)
    v = self.app.GPIO.input(channel)
    self.app.gpio_output(13, v)
