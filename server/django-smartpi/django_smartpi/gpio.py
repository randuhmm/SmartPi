from gpio_manager import shared_init, shared_command
import time


@shared_init
def init(self):
    print "test setup"
    self.app.gpio_setup(13, self.app.GPIO.OUT)
    self.app.gpio_setup(11, self.app.GPIO.IN,
                        pull_up_down=self.app.GPIO.PUD_UP)
    self.app.gpio_add_event_detect(11, self.app.GPIO.BOTH,
                                   callback=handle_on,
                                   bouncetime=200)


@shared_command
def setup(self, pin, mode, **kwargs):
    self.app.gpio_setup(pin, mode, **kwargs)


@shared_command
def cleanup(self, *args):
    return self.app.gpio_cleanup(*args)


@shared_command
def output(self, pin, value):
    self.app.gpio_output(pin, value)


@shared_command
def input(self, pin):
    return self.app.gpio_input(pin)


@shared_command
def handle_on(self, channel):
    time.sleep(0.2)
    v = self.app.GPIO.input(channel)
    self.app.gpio_output(13, v)
