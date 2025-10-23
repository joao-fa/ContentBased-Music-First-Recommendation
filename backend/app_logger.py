import logging
import os
from datetime import datetime

class AppLogger:
    def __init__(self, name: str = None):
        self.logger = logging.getLogger(name or __name__)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) %(message)s",
                datefmt="%H:%M:%S"
            )

            base_dir = os.path.dirname(os.path.abspath(__file__))
            logs_dir = os.path.join(base_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)

            log_file = os.path.join(logs_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)

            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def debug(self, message):
        self.logger.debug(message)
