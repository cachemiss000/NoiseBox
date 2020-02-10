class PrintController(object):
    def print(self, message, *args):
        pass


class SystemPrintController(PrintController):
    def print(self, message, *args):
        print(message, *args)


class MetaPrintController(PrintController):
    def __init__(self):
        self.controllers = []

    def add_print_controller(self, print_controller: PrintController):
        self.controllers.append(print_controller)

    def print(self, message, *args):
        for controller in self.controllers:
            controller.print(message, *args)


PRINT_CONTROLLER = MetaPrintController()
PRINT_CONTROLLER.add_print_controller(SystemPrintController())


def add_print_controller(print_controller: PrintController):
    PRINT_CONTROLLER.add_print_controller(print_controller)


def print_msg(message, *argv):
    PRINT_CONTROLLER.print(message, *argv)