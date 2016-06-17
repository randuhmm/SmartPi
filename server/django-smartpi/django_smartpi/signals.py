from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_smartpi.models import device_event, GpioDevice, InputDevice, OutputDevice
from django.core.exceptions import ObjectDoesNotExist


def update_pin_fields(device, pin_fields, register=True):
    for pin_field in pin_fields:
        pin_obj = getattr(device, pin_field)
        if pin_obj.registered != register:
            pin_obj.registered = register
            pin_obj.save()


def gpio_device_pre_save(sender, instance, created, update_fields, **kwargs):
    pass


def gpio_device_post_save(sender, instance, created, update_fields, **kwargs):
    if created:
        from gpio import gpio_add_device
        gpio_add_device.apply(instance)
        update_pin_fields(instance, instance.pin_fields)
    else:
        update = False
        for name, value in instance._original_gpio_fields.iteritems():
            if value != getattr(instance, name):
                update = True
                instance._original_gpio_fields[name] = getattr(instance, name)
        for name, value in instance._original_pin_fields.iteritems():
            if value != getattr(instance, name):
                update = True
                update_pin_fields(instance, [name], False)
                instance._original_pin_fields[name] = getattr(instance, name)

        if update:
            from gpio import gpio_update_device
            gpio_update_device.apply(instance)
            update_pin_fields(instance, instance.pin_fields)

    super(sender, instance).post_save(sender, created=created,
                                      update_fields=update_fields, **kwargs)


def gpio_device_post_delete(sender, instance, **kwargs):
    from gpio import gpio_delete_device
    gpio_delete_device.apply(instance)
    update_pin_fields(instance, instance.pin_fields, False)

    super(sender, instance).post_save(sender, **kwargs)


for device_class in GpioDevice.__class__.__subclasses__(GpioDevice):
    receiver(post_save, sender=device_class)(gpio_device_post_save)
    receiver(post_delete, sender=device_class)(gpio_device_post_delete)


@receiver(device_event, sender=InputDevice)
def switch_input_device_event(sender, instance, event, data, **kwargs):
    for switch in instance.switchdevice_set.all():
        switch.on_event(sender, instance, event, data)


@receiver(device_event, sender=OutputDevice)
def switch_output_device_event(sender, instance, event, data, **kwargs):
    for switch in instance.switchdevice_set.all():
        switch.on_event(sender, instance, event, data)


@receiver(device_event, sender=OutputDevice)
def gpio_output_device_event(sender, instance, event, data, **kwargs):
    try:
        instance.gpiooutputdevice.on_event(sender, instance, event, data)
    except ObjectDoesNotExist:
        pass


@receiver(post_save, sender=InputDevice)
def input_device_post_save(sender, instance, *args, **kwargs):
    instance.post_save(sender, *args, **kwargs)


@receiver(post_save, sender=OutputDevice)
def output_device_post_save(sender, instance, *args, **kwargs):
    instance.post_save(sender, *args, **kwargs)
