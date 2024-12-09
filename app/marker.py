import base64
import io
import logging
import os
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from logging import Logger
from pathlib import Path
from time import sleep

from PIL import Image
from PIL.Image import Resampling
from PIL.ImageFile import ImageFile


class Marker:
    def __init__(self, logger: Logger, max_workers: int = max(1, os.cpu_count() - 2)):
        self._max_workers = max_workers
        self._logger = logger

        self.progress_done: int = 0
        self.progress_total: int = 0
        self.running: bool = False
        self.image_for_preview_base64: str | None = None

        self.images: list[str] = []
        self.watermark_path: str | None = None
        self.output_folder: str | None = None
        self.name_extension: str = ""

    def find_images(self, folder: str) -> int:
        images = []
        for dir_entry in os.scandir(folder):
            if dir_entry.is_file() and Path(dir_entry).suffix in [".jpg", ".png", ".jpeg"]:
                images.append(dir_entry.path)
        self.images = images
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
        if not self.images or not self.watermark_path or not self.output_folder:
            raise ValueError("Missing images, watermark or output folder")
        if self.running:
            return

        self.running = True
        self.progress_total = len(self.images)
        self.progress_done = 0

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures: list[Future] = [executor.submit(
                Marker._place_mark_and_save,
                image,
                self.watermark_path,
                self.output_folder,
                self.name_extension,
                self._logger
            ) for image in self.images]

            image_base64 = None
            while futures:
                for future in futures:
                    # TODO Implement pause and stop
                    if future.done():
                        futures.remove(future)
                        image_base64, _ = future.result()
                        self.progress_done += 1
                self.image_for_preview_base64 = image_base64
                sleep(0.5)
        self.running = False

    @staticmethod
    def _place_mark_and_save(
            image_path: str, watermark_path: str, output_dir: str, name_extension: str, logger: logging.Logger) -> (
            str, str):
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
        return marked_image_base64, marked_image_path

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
