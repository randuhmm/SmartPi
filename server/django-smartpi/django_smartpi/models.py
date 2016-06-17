from __future__ import unicode_literals

from django.db import models
from django.dispatch import Signal

device_event = Signal(providing_args=['instance', 'event', 'data'])


class GpioPin(models.Model):

    PIN_5V = '5V'
    PIN_3V = '3.3V'
    PIN_GND = 'GND'
    PIN_GPIO = 'GPIO'
    PIN_DNC = 'DNC'

    PIN_CHOICES = (
        (PIN_5V, PIN_5V),
        (PIN_3V, PIN_3V),
        (PIN_GND, PIN_GND),
        (PIN_GPIO, PIN_GPIO),
        (PIN_DNC, PIN_DNC),
    )

    PROTOCOL_I2C = 'I2C'
    PROTOCOL_SPI = 'SPI'
    PROTOCOL_UART = 'UART'

    PROTOCOL_CHOICES = (
        (PROTOCOL_I2C, PROTOCOL_I2C),
        (PROTOCOL_SPI, PROTOCOL_SPI),
        (PROTOCOL_UART, PROTOCOL_UART),
    )

    def __str__(self):
        return 'PIN #%02d - %s%s%s' % (
            self.pin_number, self.pin_type,
            ' #%02d' %
            self.gpio_number if self.pin_type == GpioPin.PIN_GPIO else '',
            ' - %s %s' %
            (self.protocol_type, self.protocol_id)
            if self.protocol_type is not None else '')

    pin_number = models.IntegerField(unique=True)
    pin_type = models.CharField(max_length=4, choices=PIN_CHOICES)
    gpio_number = models.IntegerField(null=True, default=None, unique=True)
    protocol_type = models.CharField(max_length=4, choices=PROTOCOL_CHOICES,
                                     null=True, default=None, blank=True)
    protocol_id = models.CharField(max_length=4, null=True, default=None,
                                   blank=True)
    registered = models.BooleanField(default=False)


class Device(models.Model):

    related_devices = models.ManyToManyField('self', blank=True,
                                             editable=False)
    name = models.CharField(max_length=128)


class InputDevice(Device):

    state = models.BooleanField(default=False)
    _original_state = None

    def __init__(self, *args, **kwargs):
        super(InputDevice, self).__init__(*args, **kwargs)
        self._original_state = self.state

    def post_save(self, sender, **kwargs):
        if self.state != self._original_state:
            if self.state:
                device_event.send(sender=InputDevice, instance=self,
                                  event='on', data=None)
            else:
                device_event.send(sender=InputDevice, instance=self,
                                  event='off', data=None)
            self._original_state = self.state


class OutputDevice(Device):

    state = models.BooleanField(default=False)
    _original_state = None

    def __init__(self, *args, **kwargs):
        super(OutputDevice, self).__init__(*args, **kwargs)
        self._original_state = self.state

    def post_save(self, sender, **kwargs):
        if self.state != self._original_state:
            if self.state:
                device_event.send(sender=OutputDevice, instance=self,
                                  event='on', data=None)
            else:
                device_event.send(sender=OutputDevice, instance=self,
                                  event='off', data=None)
            self._original_state = self.state


class SwitchDevice(Device):

    input_device = models.ForeignKey(InputDevice)
    output_device = models.ForeignKey(OutputDevice)

    def on_event(self, sender, instance, event, data, *args):
        if self.input_device == instance:
            if event == 'on':
                self.output_device.state = True
                self.output_device.save()
            elif event == 'off':
                self.output_device.state = False
                self.output_device.save()


class Rf24Device(models.Model):
    class Meta:
        abstract = True


class GpioDevice(models.Model):

    pin_fields = []
    _original_pin_fields = None
    gpio_fields = []
    _original_gpio_fields = None

    def __init__(self, *args, **kwargs):
        super(GpioDevice, self).__init__(*args, **kwargs)
        if self.pk is not None:
            self._original_pin_fields = {}
            for pin_field in self.pin_fields:
                if not hasattr(self, pin_field):
                    raise Exception('Missing pin_field `%s` in %s' % (
                        pin_field, self))
                self._original_pin_fields[pin_field] = \
                    getattr(self, pin_field)
            self._original_gpio_fields = {}
            for gpio_field in self.gpio_fields:
                if not hasattr(self, gpio_field):
                    raise Exception('Missing gpio_field `%s` in %s' % (
                        gpio_field, self))
                self._original_gpio_fields[gpio_field] = \
                    getattr(self, gpio_field)

    class Meta:
        abstract = True

    def gpio_init(self, gpio):
        raise NotImplemented

    def gpio_reset(self, gpio):
        for pin_field in self.pin_fields:
            pin = getattr(self, pin_field).pin_number
            gpio.gpio_setup(pin, gpio.GPIO.IN)

    def gpio_cleanup(self, gpio):
        for pin_field in self.pin_fields:
            pin = getattr(self, pin_field).pin_number
            gpio.gpio_cleanup(pin)

    def post_save(self, instance, **kwargs):
        pass

    def post_delete(self, instance, **kwargs):
        pass


class GpioOutputDevice(OutputDevice, GpioDevice):

    pin_fields = ['output_pin']
    output_pin = models.OneToOneField(
        'GpioPin', limit_choices_to={
            'pin_type': GpioPin.PIN_GPIO
        })

    def gpio_init(self, gpio):
        pin = self.output_pin.pin_number
        gpio.gpio_setup(pin, gpio.GPIO.OUT)

    def on_event(self, sender, instance, event, data, *args):
        if event == 'on':
            from gpio import gpio_output
            pin = self.output_pin.pin_number
            gpio_output.apply(pin, True)
        elif event == 'off':
            from gpio import gpio_output
            pin = self.output_pin.pin_number
            gpio_output.apply(pin, False)


class GpioInputDevice(InputDevice, GpioDevice):

    pin_fields = ['input_pin']
    gpio_fields = [
        'pull_up_down',
        'edge_detect',
        'bouncetime',
    ]

    PULL_UP = 'PUP'
    PULL_DOWN = 'PDN'

    PULL_UD_CHOICES = (
        (PULL_UP, 'Use Internal Pull-Up'),
        (PULL_DOWN, 'Use Internal Pull-Down'),
    )

    EDGE_RISING = 'RISE'
    EDGE_FALLING = 'FALL'
    EDGE_BOTH = 'BOTH'

    EDGE_CHOICES = (
        (EDGE_RISING, 'Rising'),
        (EDGE_FALLING, 'Falling'),
        (EDGE_BOTH, 'Both'),
    )

    pull_up_down = models.CharField(max_length=3, choices=PULL_UD_CHOICES,
                                    null=True, default=None, blank=True)
    edge_detect = models.CharField(max_length=4, choices=EDGE_CHOICES,
                                   default=EDGE_BOTH)
    bouncetime = models.IntegerField(null=True, default=200, blank=True)
    input_pin = models.OneToOneField(
        'GpioPin', limit_choices_to={
            'pin_type': GpioPin.PIN_GPIO
        })

    def gpio_init(self, gpio):

        EDGE_MAP = {
            GpioInputDevice.EDGE_RISING: gpio.GPIO.RISING,
            GpioInputDevice.EDGE_FALLING: gpio.GPIO.FALLING,
            GpioInputDevice.EDGE_BOTH:  gpio.GPIO.BOTH,
        }

        PULL_UD_MAP = {
            GpioInputDevice.PULL_UP: gpio.GPIO.PUD_UP,
            GpioInputDevice.PULL_DOWN: gpio.GPIO.PUD_DOWN,
        }

        from django_smartpi.gpio import gpio_input
        pin = self.input_pin.pin_number
        setup_kwargs = {}
        if self.pull_up_down is not None:
            setup_kwargs['pull_up_down'] = PULL_UD_MAP[self.pull_up_down]
        event_kwargs = {
            'callback': gpio_input
        }
        if self.bouncetime is not None:
            event_kwargs['bouncetime'] = self.bouncetime
        gpio.gpio_setup(pin, gpio.GPIO.IN, **setup_kwargs)
        gpio.gpio_add_event_detect(pin, EDGE_MAP[self.edge_detect],
                                   **event_kwargs)

    def gpio_cleanup(self, gpio):
        pin = self.input_pin.pin_number
        gpio.gpio_remove_event_detect(pin)
        super(GpioInputDevice, self).gpio_cleanup(gpio)

    def gpio_reset(self, gpio):
        pin = self.input_pin.pin_number
        gpio.gpio_remove_event_detect(pin)
        super(GpioInputDevice, self).gpio_reset(gpio)

    def gpio_input(self, gpio):
        pin = self.input_pin.pin_number
        v = gpio.gpio_input(pin)
        if v != self.state:
            self.state = v
            self.save()
            print '%d - %d S' % (pin, v)
        else:
            print '%d - %d' % (pin, v)
