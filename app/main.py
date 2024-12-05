import flet
from flet.core.page import Page

from app import MarkerApp
from marker import Marker


def main(page: Page):
    page.title = "Watermarker"
    marker = Marker()
    MarkerApp(page, marker)


if __name__ == '__main__':
    flet.app(main, assets_dir="assets")
