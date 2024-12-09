import logging

import flet
from flet.core.page import Page

from app import MarkerApp
from logging_handler import MarkerLoggerHandler
from marker import Marker


def main(page: Page):
    page.title = "Watermarker"
    logger = logging.getLogger("watermarker")
    log_file_name = "watermarker.log"
    logging.basicConfig(
        filename=("%s" % log_file_name),
        encoding="utf-8",
        level=logging.ERROR,
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S%z"
    )
    marker = Marker(logger)
    marker_app = MarkerApp(page, marker)
    logger.addHandler(MarkerLoggerHandler(log_file_name, marker_app))
    marker_app.load_data()


if __name__ == '__main__':
    flet.app(main, assets_dir="assets")
