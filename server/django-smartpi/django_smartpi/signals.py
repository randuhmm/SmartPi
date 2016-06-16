from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_smartpi.models import GpioDevice


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
                break
        for name, value in instance._original_pin_fields.iteritems():
            if value != getattr(instance, name):
                update = True
                update_pin_fields(instance, [name], False)

        if update:
            from gpio import gpio_update_device
            gpio_update_device.apply(instance)
            update_pin_fields(instance, instance.pin_fields)


def gpio_device_post_delete(sender, instance, **kwargs):
    from gpio import gpio_delete_device
    gpio_delete_device.apply(instance)
    update_pin_fields(instance, instance.pin_fields, False)


for device_class in GpioDevice.__class__.__subclasses__(GpioDevice):
    receiver(post_save, sender=device_class)(gpio_device_post_save)
    receiver(post_delete, sender=device_class)(gpio_device_post_delete)
