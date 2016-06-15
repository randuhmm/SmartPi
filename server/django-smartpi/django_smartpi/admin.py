from django.contrib import admin
from django_smartpi.models import (Device, GpioDevice, GpioContactSensor,
                                   GpioDevicePin, GpioPin)


admin.site.register(Device)
admin.site.register(GpioDevice)
admin.site.register(GpioContactSensor)
admin.site.register(GpioDevicePin)
admin.site.register(GpioPin)
