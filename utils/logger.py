import logging
import os

class Logger:
    def __init__(self, name: str = __name__, log_file: str = None):
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.logger = logging.getLogger(name)
