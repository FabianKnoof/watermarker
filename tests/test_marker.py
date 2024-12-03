from unittest import TestCase

from app.marker import Marker


class TestMarker(TestCase):
    def test_place_mark(self):
        image_path = r"C:\Users\Fabian\tests\watermarker\image-copy.jpeg"
        watermark_path = r"C:\Users\Fabian\tests\watermarker\watermark.png"
        output_dir = r"C:\Users\Fabian\tests\watermarker"

        Marker.place_mark(image_path, watermark_path, output_dir, "-wm")
