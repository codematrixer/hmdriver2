import logging


class Logger:
    def __init__(self, name="my_sdk"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.handler = logging.StreamHandler()
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self._enabled = False

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if value:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.CRITICAL)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)


logger = Logger()