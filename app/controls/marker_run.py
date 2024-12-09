from subprocess import Popen
from threading import Thread
from time import sleep, time

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

        self._run_button = ft.ElevatedButton("Run", icon=ft.Icons.PLAY_CIRCLE, on_click=self._run, width=150)
        self._progress_bar = ft.ProgressBar(value=0, expand=True, height=10)
        self._progress_text = ft.Text("")

        self.controls = [self._run_button]

        self.alignment = ft.MainAxisAlignment.CENTER

    def _run(self, _):
        if self._missing_user_input():
            return

        time_start = time()
        Thread(target=self._marker.run).start()
        self._preview.loading(True)
        self._start_progress_display()

        while self._marker.running:
            sleep(0.5)
            self._update_progress_display()
            if self._marker.image_for_preview_base64:
                self._preview.show_image_base64(self._marker.image_for_preview_base64)

        self._finished(time() - time_start)
        self._preview.loading(False)

    def _update_progress_display(self) -> None:
        self._progress_bar.value = self._marker.progress_done / self._marker.progress_total
        self._progress_bar.update()
        self._progress_text.value = (f"{self._marker.progress_done:{len(str(self._marker.progress_total))}}/"
                                     f"{self._marker.progress_total:{len(str(self._marker.progress_total))}} Images "
                                     f"marked")
        self._progress_text.update()

    def _start_progress_display(self):
        pause_button = ft.IconButton(ft.Icons.PAUSE_CIRCLE, on_click=self._pause)
        cancel_button = ft.IconButton(ft.Icons.STOP_CIRCLE, on_click=self._cancel)
        self._progress_text.value = (f"{self._marker.progress_done:{len(str(self._marker.progress_total))}}/"
                                     f"{self._marker.progress_total:{len(str(self._marker.progress_total))}} Images "
                                     f"marked")
        self.controls = [self._progress_bar, self._progress_text, pause_button, cancel_button]
        self.update()

    def _finished(self, time_elapsed: float):
        alert = ft.AlertDialog(
            actions=[ft.TextButton("Ok", on_click=lambda _: self._page.close(alert)), ft.TextButton(
                "Open folder", on_click=lambda _: self._open_output_and_close_alert(alert)
            )], title=ft.Text("Done"), content=ft.Text(
                f"{len(self._marker.images)} images have been marked in {self.format_time_elapsed(time_elapsed)}"
            ), modal=True
        )
        self._page.open(alert)

        self.controls = [self._run_button]
        self._progress_bar.value = 0
        self._progress_text.value = ""
        self.update()

    def _open_output_and_close_alert(self, alert: ft.AlertDialog):
        Popen(r"explorer " + self._user_input.output_folder_text_field.value)
        self._page.close(alert)

    def _pause(self, _):
        print("Pause")

    def _cancel(self, _):
        print("Cancel")

    def _missing_user_input(self) -> bool:
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

    @staticmethod
    def format_time_elapsed(seconds: float) -> str:
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{int(hours)} hr {int(minutes)} min {int(seconds)} sec"
        elif minutes > 0:
            return f"{int(minutes)} min {int(seconds)} sec"
        else:
            return f"{int(seconds)} sec"
