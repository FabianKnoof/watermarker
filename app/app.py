from logging import Logger
from pathlib import Path
from time import sleep

import flet as ft
from flet.core.page import Page

from controls.marker_run import MarkerRun
from controls.preview import Preview
from controls.user_input import UserInput
from marker import Marker, MarkerState


class MarkerApp:

    def __init__(self, page: Page, marker: Marker, logger: Logger) -> None:
        # page.client_storage.clear()

        self._page = page
        self._marker = marker
        self._logger = logger

        self._page.window.prevent_close = True
        self._page.window.on_event = self._handle_window_event

        self._error_alert = ft.Banner(
            content=ft.Text("Oops, something didn't go right. Please check the log.", color=ft.colors.BLACK),
            leading=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.colors.AMBER),
            bgcolor=ft.colors.AMBER_100,
            actions=[ft.TextButton(
                "Ok", style=ft.ButtonStyle(color=ft.colors.BLUE), on_click=lambda _: self._page.close(self._error_alert)
            )]
        )

        self._preview = Preview("assets/preview-placeholder.png", self._marker)
        self._user_input = UserInput(self._page, self._marker, self._preview)
        self._marker_run = MarkerRun(self._page, self._marker, self._logger, self._preview, self._user_input)
        self._marker_run.width = self._user_input.width

        self._padding = 50
        self._page.window.height = self._preview.height + self._padding
        self._page.window.min_height = self._page.window.height // 2
        self._page.window.width = self._preview.width + self._user_input.width + self._padding
        self._page.window.min_width = self._page.window.width // 2
        self._page.on_resized = self._page_resized

        self._page.add(
            ft.Row(
                [ft.Column([self._user_input, ft.Divider(height=30), self._marker_run]), self._preview],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        )

    def _load_data(self) -> None:
        self._load_images_paths()
        self._load_watermark_path()
        self._load_output_folder_path()
        self._load_name_extension()
        self._load_padding()
        progress = self._load_progress()
        if progress:
            self._preview.update_preview()
        else:
            self._preview.set_preview()

    def _load_images_paths(self) -> None:
        if images := self._page.client_storage.get("watermarker.images"):
            self._marker.images = [image for image in images if Path(image).exists()]
            if self._marker.images:
                self._user_input.set_images_text()

    def _load_watermark_path(self) -> None:
        if watermark_path := self._page.client_storage.get("watermarker.watermark"):
            self._marker.watermark_path = watermark_path
            self._user_input.watermark_text_field.value = watermark_path
            self._user_input.watermark_text_field.update()

    def _load_output_folder_path(self) -> None:
        if output_folder_path := self._page.client_storage.get("watermarker.output_folder"):
            self._marker.output_folder = output_folder_path
            self._user_input.output_folder_text_field.value = output_folder_path
            self._user_input.output_folder_text_field.update()

    def _load_name_extension(self) -> None:
        if name_extension := self._page.client_storage.get("watermarker.name_extension"):
            self._marker.name_extension = name_extension
            self._user_input.name_extension_text_field.value = name_extension
            self._user_input.name_extension_text_field.update()

    def _load_padding(self):
        if padding_around := self._page.client_storage.get("watermarker.padding_around"):
            self._marker.padding_around_watermarks = padding_around
            self._user_input.padding_around_text_field.value = str(padding_around)
            self._user_input.padding_around_text_field.update()

        if padding_between := self._page.client_storage.get("watermarker.padding_between"):
            self._marker.padding_between_watermarks = padding_between
            self._user_input.padding_between_text_field.value = str(padding_between)
            self._user_input.padding_between_text_field.update()

    def _load_progress(self) -> bool:
        if (images_todo := self._page.client_storage.get("watermarker.images_todo")) and (
                images_done := self._page.client_storage.get("watermarker.images_done")):
            self._marker.resume_after_holiday(images_todo, images_done)
            self._page.client_storage.remove("watermarker.images_todo")
            self._page.client_storage.remove("watermarker.images_done")
            self._marker_run.paused()
            return True
        return False

    def _page_resized(self, e: ft.WindowResizeEvent) -> None:
        #     TODO Improve resize
        self._preview.resize(
            int(e.width - self._user_input.width - self._padding), int(e.height - self._padding)
        )
        self._preview.update()

    def _handle_window_event(self, e: ft.WindowEvent):
        if e.data == "close":
            match self._marker.state:
                case MarkerState.RUNNING:
                    exit_while_running_alert = ft.AlertDialog(
                        title=ft.Text("Watermarking still in progress!"), content=ft.Text(
                            "Do you want to save the progress and continue next time or cancel the process and exit?"
                        ), actions=[ft.TextButton(
                            "Save and exit", on_click=lambda _: self._save_and_exit(exit_while_running_alert)
                        ), ft.TextButton(
                            "Cancel and exit", on_click=lambda _: self._cancel_and_exit(exit_while_running_alert)
                        ), ft.TextButton(
                            "Don't exit", on_click=lambda _: self._page.close(exit_while_running_alert)
                        )]
                    )
                    self._page.open(exit_while_running_alert)
                case MarkerState.PAUSED:
                    paused_alert = ft.AlertDialog(
                        title=ft.Text("Watermarking paused"),
                        content=ft.Text("Do you want to save the progress to continue next time?"),
                        actions=[ft.TextButton(
                            "Yes", on_click=lambda _: self._save_and_exit(paused_alert)
                        ), ft.TextButton("No", on_click=lambda _: self._page.window.destroy()), ft.TextButton(
                            "Don't exit", on_click=lambda _: self._page.close(paused_alert)
                        )]
                    )
                    self._page.open(paused_alert)
                case MarkerState.PAUSING:
                    pausing_alert = ft.AlertDialog(
                        title=ft.Text("Watermarking pausing"),
                        content=ft.Text("Do you want to save the progress to continue next time?"),
                        actions=[ft.TextButton(
                            "Yes", on_click=lambda _: self._save_and_exit(pausing_alert)
                        ), ft.TextButton(
                            "No", on_click=lambda _: self._wait_and_exit(MarkerState.PAUSING)
                        ), ft.TextButton("Don't exit", on_click=lambda _: self._page.close(pausing_alert))]
                    )
                    self._page.open(pausing_alert)
                case MarkerState.CANCELING:
                    self._wait_and_exit(MarkerState.CANCELING)
                case _:
                    self._page.window.destroy()

    def _save_and_exit(self, alert: ft.AlertDialog | None = None) -> None:
        self._page.close(alert)
        if self._marker.state == MarkerState.RUNNING:
            self._marker_run.pause()
        while self._marker.state == MarkerState.PAUSING:
            sleep(0.1)
        self._page.client_storage.set("watermarker.images_todo", self._marker.images_todo)
        self._page.client_storage.set("watermarker.images_done", self._marker.images_done)
        self._page.window.destroy()

    def _cancel_and_exit(self, alert: ft.AlertDialog | None = None) -> None:
        self._marker_run.cancel(alert)
        self._page.window.destroy()

    def _wait_and_exit(self, state: MarkerState) -> None:
        while self._marker.state == state:
            sleep(0.1)
        self._page.window.destroy()

    def _error(self) -> None:
        self._page.open(self._error_alert)
