import logging
import os

class Logger:
    def __init__(self, name: str = __name__, log_file: str = None):
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))

        if not self.logger.handlers:
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            if log_file:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger

