from subprocess import Popen
from threading import Thread
from time import sleep

import flet as ft

from controls.preview import Preview
from controls.user_input import UserInput
from marker import Marker, MarkerState


class MarkerRun(ft.Row):

    def __init__(self, page: ft.Page, marker: Marker, preview: Preview, user_input: UserInput) -> None:
        super().__init__()

        self._page = page
        self._marker = marker
        self._preview = preview
        self._user_input = user_input

        self._run_button = ft.ElevatedButton("Run", icon=ft.Icons.PLAY_CIRCLE, on_click=self._run, width=150)
        self._pause_button = ft.IconButton(ft.Icons.PAUSE_CIRCLE, on_click=lambda _: self._marker.pause())
        self._cancel_button = ft.IconButton(ft.Icons.STOP_CIRCLE, on_click=lambda _: self._cancel_alert())
        self._progress_bar = ft.ProgressBar(value=0, expand=True, height=10)
        self._progress_text = ft.Text("")

        self.controls = [self._run_button]

        self.alignment = ft.MainAxisAlignment.CENTER

    def _run(self, _):
        if self._missing_user_input():
            return
        self._user_input_fields(True)

        Thread(target=self._marker.run).start()
        self._preview.loading(True)
        self._start_progress_display()
        while self._marker.state == MarkerState.IDLE:
            sleep(0.5)

        while self._marker.state == MarkerState.RUNNING:
            self._update_progress_display()
            if self._marker.image_for_preview_base64:
                self._preview.show_image_base64(self._marker.image_for_preview_base64)
            sleep(0.2)

        while self._marker.state == MarkerState.PAUSING:
            self._progress_bar.value = None
            self._progress_text.value = "Pausing..."
            self._pause_button.disabled = True
            self._cancel_button.disabled = True
            self.update()
            sleep(0.5)

        while self._marker.state == MarkerState.CANCELING:
            self._progress_bar.value = None
            self._progress_text.value = "Canceling..."
            self._pause_button.disabled = True
            self._cancel_button.disabled = True
            self.update()
            sleep(0.5)

        if self._marker.state == MarkerState.PAUSED:
            self._pause_button.disabled = False
            self._cancel_button.disabled = False
            self._run_button.text = "Continue"
            # TODO image amount still wrong
            self.controls = [ft.Text(
                f"Paused ({len(self._marker.images_done)}/{len(self._marker.images_todo)} Images marked)"
            ), self._run_button, self._cancel_button]
            self.update()
        elif self._marker.state == MarkerState.IDLE or self._marker.state == MarkerState.CANCELED:
            self._finished(self._marker.state == MarkerState.CANCELED)

        if self._marker.image_for_preview_base64:
            self._preview.show_image_base64(self._marker.image_for_preview_base64)
        self._preview.loading(False)

    def _update_progress_display(self) -> None:
        to_do = len(self._marker.images_todo)
        done = len(self._marker.images_done)
        self._progress_bar.value = done / to_do
        self._progress_bar.update()
        self._progress_text.value = (f"{done:{len(str(to_do))}}/"
                                     f"{to_do:{len(str(to_do))}} Images marked")
        self._progress_text.update()

    def _start_progress_display(self):
        to_do = len(self._marker.images_todo)
        done = len(self._marker.images_done)
        self._progress_text.value = (f"{done:{len(str(to_do))}}/"
                                     f"{to_do:{len(str(to_do))}} Images marked")
        self.controls = [self._progress_bar, self._progress_text, self._pause_button, self._cancel_button]
        self.update()

    def _finished(self, canceled: bool = False):
        title_text = "Canceled" if canceled else "Done"
        content_text = (f"{'The process has been canceled. ' if canceled else ''}"
                        f"{len(self._marker.images_done) + 1} images have been marked.")

        alert = ft.AlertDialog(
            actions=[ft.TextButton("Ok", on_click=lambda _: self._page.close(alert)), ft.TextButton(
                "Open folder", on_click=lambda _: self._open_output_and_close_alert(alert)
            )], title=ft.Text(title_text), content=ft.Text(content_text), modal=True
        )
        self._page.open(alert)

        self._run_button.text = "Run"
        self.controls = [self._run_button]
        self._progress_bar.value = 0
        self._progress_text.value = ""
        self._user_input_fields(False)
        self.update()

    def _open_output_and_close_alert(self, alert: ft.AlertDialog):
        Popen(r"explorer " + self._user_input.output_folder_text_field.value)
        self._page.close(alert)

    def _missing_user_input(self) -> bool:
        missing_images = self._text_field_missing_value(self._user_input.images_text_field, "Pick some images")
        missing_watermark = self._text_field_missing_value(self._user_input.watermark_text_field, "Pick a watermark")
        missing_output_folder = self._text_field_missing_value(
            self._user_input.output_folder_text_field, "Pick an output folder"
        )

        return any([missing_images, missing_watermark, missing_output_folder])

    def _cancel_alert(self):
        alert = ft.AlertDialog(
            actions=[ft.TextButton("Yes", on_click=lambda _: self._cancel(alert)),
                     ft.TextButton("No", on_click=lambda _: self._page.close(alert))],
            title=ft.Text("Cancel"),
            content=ft.Text("Do you really want to cancel the process?"),
            modal=True
        )
        self._page.open(alert)

    def _cancel(self, alert: ft.AlertDialog):
        self._page.close(alert)
        self._marker.cancel()

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

    def _user_input_fields(self, disabled: bool):
        for control in self._user_input.controls:
            control.disabled = disabled
            control.update()
