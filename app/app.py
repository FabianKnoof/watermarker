from logging import Logger

import flet as ft
from flet.core.page import Page

from controls.marker_run import MarkerRun
from controls.preview import Preview
from controls.user_input import UserInput
from marker import Marker


class MarkerApp:

    def __init__(self, page: Page, marker: Marker, logger: Logger) -> None:
        # page.client_storage.clear()

        self._page = page
        self._marker = marker
        self._logger = logger

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
        self._page.on_resized = self.page_resized

        self._page.add(
            ft.Row(
                [ft.Column([self._user_input, ft.Divider(height=30), self._marker_run]), self._preview],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        )

    #     TODO Add Alert on exit if not IDLE

    def load_data(self):
        self._user_input.load_data()

    def page_resized(self, e: ft.WindowResizeEvent):
        self._preview.resize(
            int(e.width - self._user_input.width - self._padding), int(e.height - self._padding)
        )
        self._preview.update()

    #     TODO Improve resize

    def error(self):
        self._page.open(self._error_alert)
