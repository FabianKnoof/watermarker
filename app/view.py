import os
from pathlib import Path

import flet as ft
from flet.core.page import Page

from marker import Marker


class MarkerView:

    def __init__(self, page: Page, marker: Marker) -> None:
        self.page = page
        # self.page.client_storage.clear()
        self.page.window.height = 900
        self.page.window.width = 1650
        self.marker = marker

        image_folder_picker = ft.FilePicker(on_result=self._on_image_folder_picker_result)
        self.page.overlay.append(image_folder_picker)
        pick_image_folder_button = ft.FilledTonalButton(
            "Pick image folder", on_click=lambda _: image_folder_picker.get_directory_path()
        )

        images_picker = ft.FilePicker(on_result=self._on_images_picker_result)
        self.page.overlay.append(images_picker)
        pick_images_button = ft.FilledTonalButton(
            "Pick multiple images", on_click=lambda _: images_picker.pick_files(
                allow_multiple=True, file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["png", "jpg", "jpeg"]
            )
        )

        self.images_text_field = ft.TextField(
            label="Image folder", hint_text="Path to folder containing the images", expand=True, read_only=True
        )

        watermark_picker_dialog = ft.FilePicker(on_result=self._on_watermark_picker_result)
        self.page.overlay.append(watermark_picker_dialog)
        pick_watermark_button = ft.FilledTonalButton(
            "Pick watermark image", on_click=lambda _: watermark_picker_dialog.pick_files(allowed_extensions=["png"])
        )

        self.watermark_text_field = ft.TextField(
            label="Watermark", hint_text="Path to watermark image", expand=True, read_only=True
        )

        output_folder_picker_dialog = ft.FilePicker(on_result=self._on_output_folder_picker_result)
        self.page.overlay.append(output_folder_picker_dialog)
        pick_output_folder_button = ft.FilledTonalButton(
            "Pick output folder", on_click=lambda _: output_folder_picker_dialog.get_directory_path()
        )

        self.output_folder_text_field = ft.TextField(
            label="Output folder", hint_text="Path to output folder", expand=True, read_only=True
        )

        self.name_extension_text_field = ft.TextField(
            label="Name extension",
            hint_text="Name extension will be added to the output images name",
            input_filter=ft.InputFilter(
                allow=True, regex_string=r"^[a-zA-Z-_0-9]*$", replacement_string="", ),
            on_change=self._on_change_name_extension,
            expand=True, )

        run_button = ft.ElevatedButton(text="run", icon=ft.Icons.PLAY_CIRCLE, on_click=lambda _: print("Run"))

        self.loading_circle = ft.ProgressRing(value=None, width=400, height=400, stroke_width=10)

        self.preview = ft.Image(fit=ft.ImageFit.CONTAIN, src="assets/preview-placeholder.png", width=800, height=800)
        self.preview_container = ft.Container(
            ft.Stack(
                [self.preview, self.loading_circle], alignment=ft.alignment.center
            ), border=ft.border.all(1)
        )

        self.page.add(
            ft.Row(
                [ft.Column(
                    [ft.Row(
                        [pick_images_button, pick_image_folder_button, self.images_text_field]
                    ), ft.Row(
                        [pick_watermark_button, self.watermark_text_field]
                    ), ft.Row(
                        [pick_output_folder_button, self.output_folder_text_field]
                    ), self.name_extension_text_field], width=800
                ), self.preview_container],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        )

        self._load_images_paths()
        self._load_watermark_path()
        self._load_output_folder_path()
        self._load_name_extension()  # self._update_preview()

    def _on_image_folder_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.path:
            images_amount = self.marker.find_images(e.path)
            self.preview.src = self.marker.images[0]
            self._update_preview()
            self._set_images_text(e.path, images_amount)
            self._safe_images_paths(e.path)
            self.page.update()

    def _on_images_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.files:
            self.marker.set_images([file.path for file in e.files])
            self.preview.src = self.marker.images[0]
            self._update_preview()
            self._set_images_text([vars(file) for file in e.files], len(e.files))
            self._safe_images_paths(e.files)
            self.page.update()

    def _set_images_text(self, images: list[dict] | str, images_amount: int) -> None:
        if isinstance(images, list):
            self.images_text_field.label = f"{images_amount} Images from {Path(images[0]["path"]).parent}"
            self.images_text_field.value = "; ".join([file["name"] for file in images])
        else:
            self.images_text_field.label = f"{images_amount} images"
            self.images_text_field.value = images
        self.page.update()

    def _load_images_paths(self) -> None:
        if images_data := self.page.client_storage.get("watermarker.images"):
            if isinstance(images_data, list):
                self.marker.set_images([file["path"] for file in images_data])
            else:
                self.marker.find_images(images_data)
            self.preview.src = self.marker.images[0]
            self._set_images_text(images_data, len(images_data))
            self.page.update()

    def _safe_images_paths(self, paths: list[str] | str) -> None:
        self.page.client_storage.set("watermarker.images", paths)

    def _on_watermark_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.files:
            self.marker.set_watermark(e.files[0].path)
            self.watermark_text_field.value = e.files[0].path
            self.page.client_storage.set("watermarker.watermark", e.files[0].path)
            self._update_preview()
            self.page.update()

    def _load_watermark_path(self) -> None:
        if watermark_path := self.page.client_storage.get("watermarker.watermark"):
            self.marker.set_watermark(watermark_path)
            self.watermark_text_field.value = watermark_path
            self.page.update()

    def _on_output_folder_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.path:
            self.marker.set_output_folder(e.path)
            self.output_folder_text_field.value = e.path
            self.page.client_storage.set("watermarker.output_folder", e.path)
            self.page.update()

    def _load_output_folder_path(self) -> None:
        if output_folder_path := self.page.client_storage.get("watermarker.output_folder"):
            self.marker.set_output_folder(output_folder_path)
            self.output_folder_text_field.value = output_folder_path
            self.page.update()

    def _on_change_name_extension(self, e: ft.ControlEvent):
        self.marker.set_name_extension(e.control.value)
        self.page.client_storage.set("watermarker.name_extension", e.control.value)

    def _load_name_extension(self) -> None:
        if name_extension := self.page.client_storage.get("watermarker.name_extension"):
            self.marker.set_name_extension(name_extension)
            self.name_extension_text_field.value = name_extension
            self.page.update()

    def _update_preview(self) -> None:
        if self.images_text_field.value and self.watermark_text_field.value:
            temp_folder = os.getenv("FLET_APP_STORAGE_TEMP") or "storage/temp"

            if not Path(temp_folder).exists():
                self.preview.src = "assets/preview-could-not-be-loaded.png"
            else:
                preview_path = self.marker.place_mark(
                    self.preview.src, self.marker.watermark_path, temp_folder, "", "preview.png"
                )
                self.preview.src = preview_path
            self.page.update()
