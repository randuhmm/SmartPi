from django.contrib import admin
from django import forms
from django_smartpi.models import (
    GpioInputDevice, GpioPin, GpioOutputDevice, SwitchDevice)
from django.db.models import Q


class GpioInputDeviceAdminForm(forms.ModelForm):

    model = GpioInputDevice

    def __init__(self, *args, **kwargs):
        super(GpioInputDeviceAdminForm, self).__init__(*args, **kwargs)
        if self.instance:
            pk = self.instance.pk
            qs = self.fields['input_pin'].queryset
            if pk is None:
                qs = qs.filter(registered=False)
            else:
                qs = qs.filter(
                    Q(registered=False) | Q(gpioinputdevice__pk=pk))
            self.fields['input_pin'].queryset = qs


class GpioInputDeviceAdmin(admin.ModelAdmin):
    form = GpioInputDeviceAdminForm
    list_display = [
        'name',
        'input_pin',
        'state',
    ]
    readonly_fields = ('state',)


class GpioOutputDeviceAdminForm(forms.ModelForm):

    model = GpioOutputDevice

    def __init__(self, *args, **kwargs):
        super(GpioOutputDeviceAdminForm, self).__init__(*args, **kwargs)
        if self.instance:
            pk = self.instance.pk
            qs = self.fields['output_pin'].queryset
            if pk is None:
                qs = qs.filter(registered=False)
            else:
                qs = qs.filter(
                    Q(registered=False) | Q(gpiooutputdevice__pk=pk))
            self.fields['output_pin'].queryset = qs


class GpioOutputDeviceAdmin(admin.ModelAdmin):
    form = GpioOutputDeviceAdminForm
    list_display = [
        'name',
        'output_pin',
        'state',
    ]


class GpioPinAdmin(admin.ModelAdmin):
    actions = None
    list_display = [
        '__str__',
        'pin_number',
        'pin_type',
        'gpio_number',
        'protocol_type',
        'protocol_id',
        'registered',
    ]
    readonly_fields = [
        'pin_number',
        'pin_type',
        'gpio_number',
        'protocol_type',
        'protocol_id',
        'registered',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(GpioOutputDevice, GpioOutputDeviceAdmin)
admin.site.register(GpioInputDevice, GpioInputDeviceAdmin)
admin.site.register(GpioPin, GpioPinAdmin)
admin.site.register(SwitchDevice)
