import base64
import io
import logging
import os
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from enum import Enum
from logging import Logger
from pathlib import Path
from time import sleep

from PIL import Image
from PIL.Image import Resampling
from PIL.ImageFile import ImageFile


class MarkerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    CANCELING = "canceling"
    CANCELED = "canceled"


class Marker:
    def __init__(self, logger: Logger, max_workers: int = max(1, os.cpu_count() - 2)):
        self._max_workers = max_workers
        self._logger = logger

        self._state: MarkerState = MarkerState.IDLE
        self.image_for_preview_base64: str | None = None

        self.images_todo: list[str] = []
        self.images_done: list[str] = []
        self.watermark_path: str | None = None
        self.output_folder: str | None = None
        self.name_extension: str = ""

    @property
    def state(self):
        return self._state

    def pause(self):
        self._state = MarkerState.PAUSING

    def cancel(self):
        self._state = MarkerState.CANCELING

    #         TODO Implement cancel when paused

    def find_images(self, folder: str) -> int:
        images = []
        if self._state == MarkerState.IDLE:
            for dir_entry in os.scandir(folder):
                if dir_entry.is_file() and Path(dir_entry).suffix in [".jpg", ".png", ".jpeg"]:
                    images.append(dir_entry.path)
            self.images_todo = images
        return len(images)

    def get_preview_image_base64(self, image_path: str) -> str | None:
        if not self.watermark_path:
            return None
        try:
            image = self._get_marked_image(image_path, self.watermark_path)
            image_base64 = self.convert_to_base64(image)
            image.close()
            return image_base64
        except Exception as e:
            self._logger.error("Error placing watermark!")
            self._logger.error(f"{image_path=}, {self.watermark_path=}")
            self._logger.error(e)
            self._logger.error("\n" + traceback.format_exc())
            return None

    def run(self) -> None:
        if not self.images_todo or not self.watermark_path or not self.output_folder:
            raise ValueError("Missing images, watermark or output folder")
        if self.state == MarkerState.RUNNING:
            return
        if self.state == MarkerState.CANCELED:
            self.images_todo.extend(self.images_done)
        self._state = MarkerState.RUNNING

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures: list[Future] = [executor.submit(
                Marker._place_mark_and_save,
                image,
                self.watermark_path,
                self.output_folder,
                self.name_extension,
                self._logger
            ) for image in self.images_todo]

            marked_image_base64 = None
            while futures:
                sleep(0.2)
                if self.state in [MarkerState.PAUSING, MarkerState.CANCELING]:
                    executor.shutdown(wait=True, cancel_futures=True)
                for future in futures:
                    if future.done() and not future.cancelled():
                        futures.remove(future)
                        marked_image_base64, _, image_path = future.result()
                        self.images_done.append(image_path)
                        self.images_todo.remove(image_path)
                self.image_for_preview_base64 = marked_image_base64
                if self.state in [MarkerState.PAUSING, MarkerState.CANCELING]:
                    break
        self._state_after_run()

    def _state_after_run(self):
        if not self.images_todo:
            self._state = MarkerState.IDLE
        elif self.state == MarkerState.PAUSING:
            self._state = MarkerState.PAUSED
        elif self.state == MarkerState.CANCELING:
            self._state = MarkerState.CANCELED

    @staticmethod
    def _place_mark_and_save(
            image_path: str, watermark_path: str, output_dir: str, name_extension: str, logger: logging.Logger) -> (
            str, str, str):
        try:
            marked_image = Marker._get_marked_image(image_path, watermark_path)
            marked_image_path = Marker._save_image(marked_image, output_dir, name_extension)
            marked_image_base64 = Marker.convert_to_base64(marked_image)
            marked_image.close()
        except Exception as e:
            logger.error("Error placing watermark!")
            logger.error(f"{image_path=}, {watermark_path=}, {output_dir=}, {name_extension=}")
            logger.error(e)
            logger.error(traceback.format_exc())
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
    def _get_marked_image(image_path: str, watermark_path: str) -> ImageFile:
        image = Image.open(image_path)
        with Image.open(watermark_path) as watermark:
            ratio = image.width / watermark.width
            repeats = int(image.height / (watermark.height * ratio))

            if repeats >= 1:
                watermark = watermark.resize((image.width, int(watermark.height * ratio)), resample=Resampling.LANCZOS)
                offset = (image.height - (repeats * watermark.height)) // 2
                for i in range(repeats):
                    image.paste(watermark, (0, offset + i * watermark.height), watermark)
            else:
                ratio = image.height / watermark.height
                watermark = watermark.resize((int(watermark.width * ratio), image.height), resample=Resampling.LANCZOS)
                repeats = image.width // watermark.width
                offset = (image.width - (repeats * watermark.width)) // 2
                for i in range(repeats):
                    image.paste(watermark, (offset + i * watermark.width, 0), watermark)
        return image

    @staticmethod
    def convert_to_base64(image: ImageFile) -> str:
        buffered = io.BytesIO()
        image.save(buffered, image.format.lower())
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
