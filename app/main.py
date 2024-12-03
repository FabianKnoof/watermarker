import flet
from flet.core.page import Page

from marker import Marker
from view import MarkerView

if __name__ == '__main__':
    # root_dir = r"C:\Users\Fabian\tests\watermarker\fav"
    # watermark_path = r"C:\Users\Fabian\tests\watermarker\watermark.png"
    # output_dir = r"C:\Users\Fabian\tests\watermarker\wm"
    #
    # marker = Marker()
    # marker.run(root_dir, watermark_path, output_dir, "-wm")

    def main(page: Page):
        page.title = "Watermarker"
        marker = Marker()
        MarkerView(page, marker)


    flet.app(main, assets_dir="assets")
