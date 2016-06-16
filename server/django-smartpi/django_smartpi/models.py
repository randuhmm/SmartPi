from __future__ import unicode_literals

from django.db import models


class Device(models.Model):
    parent = models.ForeignKey('self', blank=True, null=True, editable=False)
    name = models.CharField(max_length=128)


class InputDevice(Device):
    state = models.BooleanField(default=False)


class OutputDevice(Device):
    state = models.BooleanField(default=False)

    _original_state = None

    def __init__(self, *args, **kwargs):
        super(OutputDevice, self).__init__(*args, **kwargs)
        self._original_state = self.state

    def save(self, *args, **kwargs):
        super(OutputDevice, self).save(*args, **kwargs)
        if self.state != self._original_state:
            if self.state:
                self.on()
            else:
                self.off()
            self._original_state = self.state

    def on(self):
        raise NotImplemented

    def off(self):
        raise NotImplemented


class Rf24Device(models.Model):
    class Meta:
        abstract = True


class GpioDevice(models.Model):

    pin_fields = []

    _update_gpio_on_save = False
    _original_pin_fields = {}

    def __init__(self, *args, **kwargs):
        super(GpioDevice, self).__init__(*args, **kwargs)
        if self.pk is not None:
            for pin_field in self.pin_fields:
                if not hasattr(self, pin_field):
                    raise Exception('Missing attribute `%s` in %s' % (
                        pin_field, self))
                self._original_pin_fields[pin_field] = getattr(self, pin_field)

    def save(self, *args, **kwargs):
        inserting = self.pk is None
        super(GpioDevice, self).save(*args, **kwargs)
        if inserting:
            from gpio import gpio_add_device
            gpio_add_device.apply(self)
        elif self._update_gpio_on_save:
            from gpio import gpio_update_device
            gpio_update_device.apply(self)

    def delete(self, *args, **kwargs):
        super(GpioDevice, self).delete(*args, **kwargs)
        from gpio import gpio_delete_device
        gpio_delete_device.apply(self)

    def update_gpio_on_save(self):
        self._update_gpio_on_save = True

    class Meta:
        abstract = True

    def gpio_init(self, gpio):
        raise NotImplemented

    def gpio_reset(self, gpio):
        for pin_field in self.pin_fields:
            pin = getattr(self, pin_field).pin.pin_number
            gpio.gpio_setup(pin, gpio.GPIO.IN)

    def gpio_cleanup(self, gpio):
        for pin_field in self.pin_fields:
            pin = getattr(self, pin_field).pin.pin_number
            gpio.gpio_cleanup(pin)


class GpioOutputDevice(OutputDevice, GpioDevice):

    pin_fields = ['output_pin']

    output_pin = models.OneToOneField('GpioDevicePin',
                                      on_delete=models.CASCADE)

    def gpio_init(self, gpio):
        pin = self.output_pin.pin.pin_number
        gpio.gpio_setup(pin, gpio.GPIO.OUT)

    def on(self):
        from gpio import gpio_output
        pin = self.output_pin.pin.pin_number
        gpio_output.apply(pin, True)

    def off(self):
        from gpio import gpio_output
        pin = self.output_pin.pin.pin_number
        gpio_output.apply(pin, False)


class GpioInputDevice(InputDevice, GpioDevice):

    pin_fields = ['input_pin']

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
    input_pin = models.OneToOneField('GpioDevicePin',
                                     on_delete=models.CASCADE)

    _original_pull_up_down = None
    _original_edge_detect = None
    _original_bouncetime = None

    def __init__(self, *args, **kwargs):
        super(GpioInputDevice, self).__init__(*args, **kwargs)
        self._original_pull_up_down = self.pull_up_down
        self._original_edge_detect = self.edge_detect
        self._original_bouncetime = self.bouncetime

    def save(self, *args, **kwargs):
        if self.pk is None:
            pass
        elif self.pull_up_down != self._original_pull_up_down or \
                self.edge_detect != self._original_edge_detect or \
                self.bouncetime != self._original_bouncetime:
            self.update_gpio_on_save()
        super(GpioInputDevice, self).save(*args, **kwargs)
        self._original_pull_up_down = self.pull_up_down
        self._original_edge_detect = self.edge_detect
        self._original_bouncetime = self.bouncetime

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
        pin = self.input_pin.pin.pin_number
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
        pin = self.input_pin.pin.pin_number
        gpio.gpio_remove_event_detect(pin)
        super(GpioInputDevice, self).gpio_cleanup(gpio)

    def gpio_reset(self, gpio):
        pin = self.input_pin.pin.pin_number
        gpio.gpio_remove_event_detect(pin)
        super(GpioInputDevice, self).gpio_reset(gpio)

    def gpio_input(self, gpio):
        pin = self.input_pin.pin.pin_number
        v = gpio.gpio_input(pin)
        if v != self.state:
            self.state = v
            self.save()
            print '%d - %d S' % (pin, v)
        else:
            print '%d - %d' % (pin, v)


class GpioDevicePin(models.Model):
    pin = models.OneToOneField('GpioPin', on_delete=models.CASCADE,
                               unique=True)

    def __str__(self):
        return '%d' % self.pin.pin_number


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
        return '%d' % self.pin_number

    pin_number = models.IntegerField(unique=True)
    pin_type = models.CharField(max_length=4, choices=PIN_CHOICES)
    gpio_number = models.IntegerField(null=True, default=None, unique=True)
    protocol_type = models.CharField(max_length=4, choices=PROTOCOL_CHOICES,
                                     null=True, default=None, blank=True)
    protocol_id = models.CharField(max_length=4, null=True, default=None,
                                   blank=True)
