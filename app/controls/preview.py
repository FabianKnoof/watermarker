import flet as ft

from marker import Marker


class Preview(ft.Stack):
    def __init__(self, image_src: str, marker: Marker) -> None:
        super().__init__()

        self._marker = marker

        self._image = ft.Image(src=image_src, fit=ft.ImageFit.CONTAIN)
        self._progress_ring = ft.ProgressRing(value=None, stroke_width=10, visible=False)
        self.resize(800, 800)

        self.controls = [self._image, self._progress_ring]

        self.alignment = ft.alignment.center

    def show_image_base64(self, image_as_base64: str) -> None:
        self._image.src_base64 = image_as_base64
        self._image.update()

    def show_image(self, path: str) -> None:
        self._image.src = path
        self._image.update()

    def loading(self, value: bool) -> None:
        self._progress_ring.visible = value
        self._progress_ring.update()

    def show_marked_image(self, image_path: str) -> None:
        self.loading(True)
        image_base64 = self._marker.get_preview_image_base64(image_path)
        if image_base64:
            self.show_image_base64(image_base64)
        self.loading(False)

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._image.width = width
        self._image.height = height
        self._progress_ring.width = width // 2
        self._progress_ring.height = height // 2
