import os
from pathlib import Path

import flet as ft

from controls.preview import Preview
from marker import Marker


class UserInput(ft.Column):
    def __init__(self, page: ft.Page, marker: Marker, preview: Preview):
        super().__init__()

        self._page = page
        self._marker = marker
        self._preview = preview

        pick_buttons_width = 170
        text_fields_width = 500

        image_folder_picker = ft.FilePicker(on_result=self._on_image_folder_picker_result)
        page.overlay.append(image_folder_picker)
        pick_image_folder_button = ft.FilledTonalButton(
            "Pick image folder", on_click=lambda _: image_folder_picker.get_directory_path(), width=pick_buttons_width
        )

        images_picker = ft.FilePicker(on_result=self._on_images_picker_result)
        page.overlay.append(images_picker)
        pick_images_button = ft.FilledTonalButton(
            "Pick multiple images", on_click=lambda _: images_picker.pick_files(
                allow_multiple=True, file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["png", "jpg", "jpeg"]
            ), width=pick_buttons_width
        )

        self.images_text_field = ft.TextField(
            label="Image folder",
            hint_text="Path to folder containing the images",
            expand=True,
            read_only=True,
            width=text_fields_width
        )

        watermark_picker_dialog = ft.FilePicker(on_result=self._on_watermark_picker_result)
        page.overlay.append(watermark_picker_dialog)
        pick_watermark_button = ft.FilledTonalButton(
            "Pick watermark image",
            on_click=lambda _: watermark_picker_dialog.pick_files(allowed_extensions=["png"]),
            width=pick_buttons_width
        )

        self.watermark_text_field = ft.TextField(
            label="Watermark", hint_text="Path to watermark image", expand=True, read_only=True, width=text_fields_width
        )

        output_folder_picker_dialog = ft.FilePicker(on_result=self._on_output_folder_picker_result)
        page.overlay.append(output_folder_picker_dialog)
        pick_output_folder_button = ft.FilledTonalButton(
            "Pick output folder",
            on_click=lambda _: output_folder_picker_dialog.get_directory_path(),
            width=pick_buttons_width
        )

        self.output_folder_text_field = ft.TextField(
            label="Output folder",
            hint_text="Path to output folder",
            expand=True,
            read_only=True,
            width=text_fields_width
        )

        self._name_extension_text_field = ft.TextField(
            label="Name extension",
            hint_text="Name extension will be added to the output images name",
            input_filter=ft.InputFilter(
                allow=True, regex_string=r"^[a-zA-Z-_0-9]*$", replacement_string="", ),
            on_change=self._on_change_name_extension,
            expand=True,
            width=text_fields_width
        )

        pick_buttons_row_width = 400
        pick_buttons_alignment = ft.MainAxisAlignment.START
        pick_buttons_cross_alignment = ft.CrossAxisAlignment.CENTER

        self.controls = [ft.Row(
            [self.images_text_field, ft.Row(
                [pick_images_button, ft.Text("or"), pick_image_folder_button],
                width=pick_buttons_row_width,
                alignment=pick_buttons_alignment,
                vertical_alignment=pick_buttons_cross_alignment
            )]
        ), ft.Row(
            [self.watermark_text_field, ft.Row(
                [pick_watermark_button],
                width=pick_buttons_row_width,
                alignment=pick_buttons_alignment,
                vertical_alignment=pick_buttons_cross_alignment
            )]
        ), ft.Row(
            [self.output_folder_text_field, ft.Row(
                [pick_output_folder_button],
                width=pick_buttons_row_width,
                alignment=pick_buttons_alignment,
                vertical_alignment=pick_buttons_cross_alignment
            )]
        ), ft.Row(
            [self._name_extension_text_field, ft.Row([ft.Container()], width=pick_buttons_row_width)]
        )]

        self.width = text_fields_width + pick_buttons_row_width

    def _on_image_folder_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.path:
            self._marker.images = self._marker.find_images(e.path)

            if self._marker.images:
                self._update_preview()

                self._set_images_text(e.path, len(self._marker.images))
                self._safe_images_paths(e.path)
            else:
                self.images_text_field.error_text = "No images found in the folder"
                self.images_text_field.update()

    def _on_images_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.files:
            self._marker.images = [file.path for file in e.files]

            self._update_preview()

            self._set_images_text([file for file in e.files], len(self._marker.images))
            self._safe_images_paths(e.files)

    def _on_watermark_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.files:
            self._marker.watermark_path = e.files[0].path
            self.watermark_text_field.value = e.files[0].path
            self.watermark_text_field.error_text = ""
            self.watermark_text_field.update()

            self._page.client_storage.set("watermarker.watermark", e.files[0].path)
            self._update_preview()

    def _on_output_folder_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.path:
            if self.output_folder_is_empty(e.path):
                self._update_output_folder(e.path)
            else:
                output_folder_not_empty_alert = ft.AlertDialog(
                    title=ft.Text("Output folder is not empty. Do you still want to use it?"), content=ft.Text(
                        "If resulting images have the same name as images already in "
                        "the output folder, they will overwrite them!"
                    ), actions=[ft.TextButton(
                        "Yes", on_click=lambda _: self._output_folder_alert_yes(output_folder_not_empty_alert, e.path)
                    ), ft.TextButton("No", on_click=lambda _: self._page.close(output_folder_not_empty_alert))]
                )
                self._page.open(output_folder_not_empty_alert)

    @staticmethod
    def output_folder_is_empty(path: str) -> bool:
        return not any(os.scandir(path))

    def _output_folder_alert_yes(self, alert: ft.AlertDialog, path: str) -> None:
        self._page.close(alert)
        self._update_output_folder(path)

    def _update_output_folder(self, path: str) -> None:
        self._marker.output_folder = path
        self.output_folder_text_field.value = path
        self.output_folder_text_field.error_text = ""
        self.output_folder_text_field.update()
        self._page.client_storage.set("watermarker.output_folder", path)

    def _on_change_name_extension(self, e: ft.ControlEvent):
        self._marker.name_extension = e.control.value
        self._page.client_storage.set("watermarker.name_extension", e.control.value)

    def _set_images_text(self, images: list[dict] | str, images_amount: int) -> None:
        if isinstance(images, list):
            self.images_text_field.label = f"{images_amount} Images from {Path(images[0]["path"]).parent}"
            self.images_text_field.value = "; ".join([file["name"] for file in images])
        else:
            self.images_text_field.label = f"{images_amount} images"
            self.images_text_field.value = images
        self.images_text_field.error_text = ""
        self.images_text_field.update()

    def _update_preview(self) -> None:
        if self.images_text_field.value:
            if self.watermark_text_field.value:
                self._preview.show_marked_image(self._marker.images[0])
            else:
                self._preview.show_image(self._marker.images[0])
        else:
            self._preview.show_image("assets/preview-placeholder.png")

    def load_data(self) -> None:
        self._load_images_paths()
        self._load_watermark_path()
        self._load_output_folder_path()
        self._load_name_extension()
        self._update_preview()

    def _load_images_paths(self) -> None:
        if images_data := self._page.client_storage.get("watermarker.images"):
            if isinstance(images_data, list):
                self._marker.images = [file["path"] for file in images_data]
            else:
                self._marker.images = self._marker.find_images(images_data)

            self._set_images_text(images_data, len(self._marker.images))

    def _load_watermark_path(self) -> None:
        if watermark_path := self._page.client_storage.get("watermarker.watermark"):
            self._marker.watermark_path = watermark_path
            self.watermark_text_field.value = watermark_path
            self.watermark_text_field.update()

    def _load_output_folder_path(self) -> None:
        if output_folder_path := self._page.client_storage.get("watermarker.output_folder"):
            self._marker.output_folder = output_folder_path
            self.output_folder_text_field.value = output_folder_path
            self.output_folder_text_field.update()

    def _load_name_extension(self) -> None:
        if name_extension := self._page.client_storage.get("watermarker.name_extension"):
            self._marker.name_extension = name_extension
            self._name_extension_text_field.value = name_extension
            self._name_extension_text_field.update()

    def _safe_images_paths(self, paths: list[str] | str) -> None:
        self._page.client_storage.set("watermarker.images", paths)
