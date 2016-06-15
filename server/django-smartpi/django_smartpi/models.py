from __future__ import unicode_literals

from django.db import models


class Device(models.Model):
    parent = models.ForeignKey('self', blank=True, null=True, editable=False)
    name = models.CharField(max_length=128)



class Rf24Device(Device):
    pass



class GpioDevice(Device):
    pins = []

    def gpio_init(self):
        pass


class GpioContactSensor(GpioDevice):
    pins = {
        'contact':
    }


class GpioDevicePin(models.Model):
    device = models.OneToOneField(GpioDevice, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)


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

    pin_number = models.IntegerField()
    pin_type = models.CharField(max_length=4, choices=PIN_CHOICES)
    gpio_number = models.IntegerField(null=True, default=None)
    protocol_type = models.CharField(max_length=4, choices=PROTOCOL_CHOICES,
                                     null=True, default=None, blank=True)
    protocol_id = models.CharField(max_length=4, null=True, default=None,
                                   blank=True)
    device = models.ForeignKey(GpioDevicePin, on_delete=models.SET_NULL,
                               blank=True, null=True,)
