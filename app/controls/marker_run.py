import flet as ft

from controls.preview import Preview
from controls.user_input import UserInput
from marker import Marker


class MarkerRun(ft.Row):

    def __init__(self, page: ft.Page, marker: Marker, preview: Preview, user_input: UserInput) -> None:
        super().__init__()

        self._page = page
        self._marker = marker
        self._preview = preview
        self._user_input = user_input

        self._run_button = ft.ElevatedButton("Run", icon=ft.icons.PLAY_CIRCLE, on_click=self._run, width=150)

        self.controls = [self._run_button]

        self.alignment = ft.MainAxisAlignment.CENTER

    def _run(self, _):
        if not self._filled_text_fields():
            return



    def _filled_text_fields(self) -> bool:
        missing_images = self._text_field_missing_value(self._user_input.images_text_field, "Pick some images")
        missing_watermark = self._text_field_missing_value(self._user_input.watermark_text_field, "Pick a watermark")
        missing_output_folder = self._text_field_missing_value(
            self._user_input.output_folder_text_field, "Pick an output folder"
        )

        return any([missing_images, missing_watermark, missing_output_folder])

    @staticmethod
    def _text_field_missing_value(text_field: ft.TextField, error_text: str) -> bool:
        if not text_field.value:
            text_field.error_text = error_text
            text_field.update()
            return True
        return False
