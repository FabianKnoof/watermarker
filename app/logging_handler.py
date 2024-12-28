import logging

from app import MarkerApp


class MarkerLoggerHandler(logging.FileHandler):
    def __init__(self, filename: str, app: MarkerApp):
        super().__init__(filename, encoding="utf-8")
        self._app = app

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self._app._error()
