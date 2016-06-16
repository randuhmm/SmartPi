from django.contrib import admin
from django_smartpi.models import (
    GpioInputDevice, GpioDevicePin, GpioPin, GpioOutputDevice)


admin.site.register(GpioOutputDevice)
admin.site.register(GpioInputDevice)
admin.site.register(GpioDevicePin)
admin.site.register(GpioPin)
