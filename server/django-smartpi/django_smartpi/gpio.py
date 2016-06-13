from gpio_manager import gpio


@gpio.setup
def setup_gpio():
    print "SETUP GPIO"
