from logging import Logger
from subprocess import Popen
from time import sleep

import flet as ft

from controls.preview import Preview
from controls.user_input import UserInput
from marker import Marker, MarkerState, StateChangeError


class MarkerRun(ft.Row):

    def __init__(self, page: ft.Page, marker: Marker, logger: Logger, preview: Preview, user_input: UserInput) -> None:
        super().__init__()

        self._page = page
        self._marker = marker
        self._logger = logger
        self._preview = preview
        self._user_input = user_input

        self._UPDATE_INTERVAL = 0.2

        self._run_button = ft.ElevatedButton("Run", icon=ft.Icons.PLAY_CIRCLE, on_click=self._run, width=150)
        self._pause_button = ft.IconButton(ft.Icons.PAUSE_CIRCLE, on_click=self._pause)
        self._cancel_button = ft.IconButton(ft.Icons.STOP_CIRCLE, on_click=lambda _: self._cancel_alert())
        self._progress_bar = ft.ProgressBar(value=0, expand=True, height=10)
        self._progress_text = ft.Text("")

        self.controls = [self._run_button]

        self.alignment = ft.MainAxisAlignment.CENTER

    def _run(self, _):
        if self._missing_user_input():
            return
        # TODO Check output folder content
        self._disable_user_input_fields(True)
        if self._marker.state == MarkerState.IDLE and not self._marker.images_todo and self._marker.images_done:
            self._marker.images_todo = self._marker.images_done
            self._marker.images_done = []

        try:
            self._marker.set_state("run")
        except StateChangeError as e:
            self._logger.error(e, exc_info=True)
        self._preview.loading(True)
        self._start_progress_display()

        while self._marker.state == MarkerState.RUNNING:
            self._update_progress_display()
            if self._marker.image_for_preview_base64:
                self._preview.show_image_base64(self._marker.image_for_preview_base64)
            sleep(self._UPDATE_INTERVAL)

        if self._marker.state == MarkerState.IDLE:
            self._finished()

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

    def _start_progress_display(self):
        done = len(self._marker.images_done)
        total = len(self._marker.images_todo) + done
        self._progress_text.value = (f"{done:{len(str(total))}}/"
                                     f"{total:{len(str(total))}} Images marked")
        self.controls = [self._progress_bar, self._progress_text, self._pause_button, self._cancel_button]
        self.update()

    def _update_progress_display(self) -> None:
        done = len(self._marker.images_done)
        total = len(self._marker.images_todo) + done
        self._progress_text.value = (f"{done:{len(str(total))}}/"
                                     f"{total:{len(str(total))}} Images marked")
        self._progress_text.update()
        self._progress_bar.value = done / len(self._marker.images_todo)
        self._progress_bar.update()

    def _pause(self, _):
        try:
            self._marker.set_state("pause")
        except StateChangeError as e:
            self._logger.error(e, exc_info=True)

        while self._marker.state == MarkerState.PAUSING:
            self._progress_bar.value = None
            self._progress_text.value = "Pausing..."
            self._pause_button.disabled = True
            self._cancel_button.disabled = True
            sleep(self._UPDATE_INTERVAL)

        self._pause_button.disabled = False
        self._cancel_button.disabled = False
        self._run_button.text = "Continue"
        self.controls = [ft.Text(
            f"Paused ({len(self._marker.images_done)}/{len(self._marker.images_todo) + len(self._marker.images_done)} "
            f"Images marked)"
        ), self._run_button, self._cancel_button]
        self.update()

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
        try:
            self._marker.set_state("cancel")
        except StateChangeError as e:
            self._logger.error(e, exc_info=True)

        while self._marker.state == MarkerState.CANCELING:
            self._progress_bar.value = None
            self._progress_text.value = "Canceling..."
            self._pause_button.disabled = True
            self._cancel_button.disabled = True
            self._page.update(self._progress_bar, self._progress_text, self._pause_button, self._cancel_button)
            sleep(self._UPDATE_INTERVAL)

        self._finished(canceled=True)

    def _finished(self, canceled: bool = False):
        title_text = "Canceled" if canceled else "Done"
        content_text = (f"{'The process has been canceled. ' if canceled else ''}"
                        f"{len(self._marker.images_done)} images have been marked.")

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
        self._disable_user_input_fields(False)
        if self._marker.image_for_preview_base64:
            self._preview.show_image_base64(self._marker.image_for_preview_base64)
        self._preview.loading(False)
        self.update()

    def _open_output_and_close_alert(self, alert: ft.AlertDialog):
        Popen(r"explorer " + self._user_input.output_folder_text_field.value)
        self._page.close(alert)

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

    def _disable_user_input_fields(self, disabled: bool):
        for control in self._user_input.controls:
            control.disabled = disabled
            control.update()
