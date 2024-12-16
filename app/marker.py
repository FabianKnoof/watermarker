import base64
import io
import logging
import os
from concurrent.futures import Future, ThreadPoolExecutor
from enum import Enum
from logging import Logger
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Literal

from PIL import Image
from PIL.Image import Resampling
from PIL.ImageFile import ImageFile


class MarkerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    CANCELING = "canceling"


class StateChangeError(Exception):

    def __init__(
            self, message: str, from_state: MarkerState, to_state: MarkerState | Literal["run", "pause", "cancel"]):
        super().__init__(message)
        self.from_state = from_state
        self.to_state = to_state


class Marker:

    def __init__(self, logger: Logger, max_workers: int = max(1, os.cpu_count() - 2)):
        self._max_workers = max_workers
        self._logger = logger

        self._state: MarkerState = MarkerState.IDLE
        self.image_for_preview_base64: str | None = None
        self.UPDATE_INTERVAL = 0.2

        self.images: list[str] = []
        self._images_todo: list[str] = []
        self._images_done: list[str] = []
        self.watermark_path: str | None = None
        self.output_folder: str | None = None
        self.name_extension: str = ""
        self.padding_around_watermarks: int = 0
        self.padding_between_watermarks: int = 0

    @property
    def state(self) -> MarkerState:
        return self._state

    def amount_images_todo(self) -> int:
        return len(self._images_todo)

    def amount_images_done(self) -> int:
        return len(self._images_done)

    def set_state(self, new_state: Literal["run", "pause", "cancel"]) -> None:
        match new_state:
            case "run" if self.state in [MarkerState.IDLE, MarkerState.PAUSED]:
                if self.state == MarkerState.IDLE:
                    missing_items = [item for item, condition in
                                     [("images", self.images), ("watermark", self.watermark_path),
                                      ("output folder", self.output_folder)] if not condition]
                    if missing_items:
                        raise StateChangeError(
                            f"Missing {', '.join(missing_items)}", self.state, MarkerState.RUNNING
                        )
                    self._images_todo = self.images.copy()
                    self._images_done = []
                self._state = MarkerState.RUNNING
                Thread(target=self._run).start()
            case "pause" if self.state == MarkerState.RUNNING:
                self._state = MarkerState.PAUSING
            case "cancel" if self.state == MarkerState.RUNNING:
                self._state = MarkerState.CANCELING
            case "cancel" if self.state == MarkerState.PAUSED:
                self._images_todo.extend(self._images_done)
                self._state = MarkerState.IDLE
            case _:
                raise StateChangeError(
                    f"Can't do state change from {self._state} to {new_state}", self._state, new_state
                )

    def _run(self) -> None:
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures: list[Future] = [executor.submit(
                Marker._place_mark_and_save,
                image,
                self.watermark_path,
                self.output_folder,
                self.name_extension,
                self.padding_around_watermarks,
                self.padding_between_watermarks,
                self._logger
            ) for image in self._images_todo]

            marked_image_base64 = self.image_for_preview_base64
            # TODO Improve marked_image_base64 and preview assignment
            while futures:
                sleep(self.UPDATE_INTERVAL)

                if self.state in [MarkerState.PAUSING, MarkerState.CANCELING]:
                    executor.shutdown(wait=True, cancel_futures=True)

                finished_futures = []
                for future in futures:
                    if future.done() and not future.cancelled():
                        finished_futures.append(future)
                        marked_image_base64, _, image_path = future.result()
                        self._images_done.append(image_path)
                        self._images_todo.remove(image_path)
                [futures.remove(finished_future) for finished_future in finished_futures]
                self.image_for_preview_base64 = marked_image_base64

                if self.state == MarkerState.PAUSING:
                    self._state = MarkerState.PAUSED
                    return
                elif not self._images_todo or self.state == MarkerState.CANCELING:
                    self._state = MarkerState.IDLE
                    return

    @staticmethod
    def find_images(folder: str) -> list[str]:
        images = []
        for dir_entry in os.scandir(folder):
            if dir_entry.is_file() and Path(dir_entry).suffix in [".jpg", ".png", ".jpeg"]:
                images.append(dir_entry.path)
        return images

    def get_preview_image_base64(self, image_path: str) -> str | None:
        if not self.watermark_path:
            return None
        # noinspection PyBroadException
        try:
            with self._get_marked_image(
                    image_path, self.watermark_path, self.padding_around_watermarks, self.padding_between_watermarks
            ) as image:
                image_base64 = self.convert_to_base64(image)
                return image_base64
        except Exception:
            self._logger.error("Error placing watermark!", exc_info=True)
            self._logger.error(f"{image_path=}, {self.watermark_path=}")
            return None

    @staticmethod
    def _place_mark_and_save(
            image_path: str,
            watermark_path: str,
            output_dir: str,
            name_extension: str,
            padding_around: int,
            padding_between: int,
            logger: logging.Logger) -> (str, str, str):
        # noinspection PyBroadException
        try:
            with Marker._get_marked_image(image_path, watermark_path, padding_around, padding_between) as marked_image:
                marked_image_path = Marker._save_image(marked_image, output_dir, name_extension)
                marked_image_base64 = Marker.convert_to_base64(marked_image)
        except Exception:
            logger.error("Error placing watermark!", exc_info=True)
            logger.error(f"{image_path=}, {watermark_path=}")
            marked_image_base64 = ""
            marked_image_path = ""
        return marked_image_base64, marked_image_path, image_path

    @staticmethod
    def _save_image(image: ImageFile, output_dir: str, name_extension: str) -> str:
        marked_file_name = f"{Path(image.filename).stem}{name_extension}{Path(image.filename).suffix}"
        marked_file_path = Path(output_dir).joinpath(marked_file_name)
        image.save(marked_file_path)
        return str(marked_file_path)

    @staticmethod
    def _get_marked_image(
            image_path: str, watermark_path: str, padding_around: int, padding_between: int) -> ImageFile:
        image = Image.open(image_path)
        with Image.open(watermark_path) as watermark:
            # Calculate watermark dimensions assuming vertical stack
            watermark_scaled_width = image.width - 2 * padding_around
            ratio = watermark_scaled_width / watermark.width
            watermark_scaled_height = int(watermark.height * ratio)
            relevant_dimension = watermark_scaled_height

            # Adjust dimensions if vertical stack doesn't fit
            if (watermark_scaled_height + 2 * padding_around) > image.height:
                watermark_scaled_height = image.height - 2 * padding_around
                ratio = watermark_scaled_height / watermark.height
                watermark_scaled_width = int(watermark.width * ratio)
                relevant_dimension = watermark_scaled_width

            watermark = watermark.resize(
                (watermark_scaled_width, watermark_scaled_height), resample=Resampling.LANCZOS
            )
            repeats = int(
                (image.height - 2 * padding_around + padding_between) / (relevant_dimension + padding_between)
            )
            offset = (image.height - (repeats * (relevant_dimension + padding_between) - padding_between)) // 2

            for repeat in range(repeats):
                if relevant_dimension == watermark_scaled_height:
                    position = (padding_around, offset + repeat * (watermark_scaled_height + padding_between))
                else:
                    position = (offset + repeat * (watermark_scaled_width + padding_between), padding_around)
                image.paste(watermark, position, watermark)
            return image

    @staticmethod
    def convert_to_base64(image: ImageFile) -> str:
        buffered = io.BytesIO()
        image.save(buffered, image.format.lower())
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
