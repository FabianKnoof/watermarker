import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep, time

from PIL import Image
from PIL.Image import Resampling


class Marker:
    def __init__(self):
        self.progress_done: int = 0
        self.progress_total: int = 0
        self.time_start: float | None = None
        self.time_elapsed: float | None = None

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

    def set_images(self, images: list[str]) -> None:
        self.images = images

    def set_watermark(self, watermark_path: str) -> None:
        self.watermark_path = watermark_path

    def set_output_folder(self, output_folder: str) -> None:
        self.output_folder = output_folder

    def set_name_extension(self, name_extension: str) -> None:
        self.name_extension = name_extension

    def place_markers(self) -> None:
        self.progress_total = len(self.images)
        self.time_start = time()

        max_workers = max(1, os.cpu_count() - 2)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(Marker.place_mark, image, self.watermark_path, self.output_folder, self.name_extension)
                for image in self.images]

            while futures:
                for future in futures:
                    if future.done():
                        futures.remove(future)
                        self.progress_done += 1
                self.time_elapsed = time() - self.time_start
                print(
                    f"\rProcessed {self.progress_done}/{self.progress_total}, Time elapsed: "
                    f"{self.pretty_format_time(self.time_elapsed)}", end=""
                )
                sleep(0.5)
            print(
                f"\rFinished {self.progress_done}/{self.progress_total}, Time taken: "
                f"{self.pretty_format_time(self.time_elapsed):}"
            )

    @staticmethod
    def place_mark(
            image_path: str,
            watermark_path: str,
            output_dir: str,
            name_extension: str,
            new_file_name: str | None = None) -> str:
        image_path = Path(image_path)
        image = Image.open(image_path)
        watermark = Image.open(watermark_path)

        ratio = image.width // watermark.width
        repeats = image.height // (watermark.height * ratio)

        if repeats >= 1:
            watermark = watermark.resize((image.width, watermark.height * ratio), resample=Resampling.LANCZOS)
            offset = (image.height - (repeats * watermark.height)) // 2
            for i in range(repeats):
                image.paste(watermark, (0, offset + i * watermark.height), watermark)
        else:
            ratio = image.height // watermark.height
            watermark = watermark.resize((watermark.width * ratio, image.height), resample=Resampling.LANCZOS)
            repeats = image.width // watermark.width
            offset = (image.width - (repeats * watermark.width)) // 2
            for i in range(repeats):
                image.paste(watermark, (offset + i * watermark.width, 0), watermark)

        marked_file_name = new_file_name or f"{image_path.stem}{name_extension}{image_path.suffix}"
        marked_file_path = Path(output_dir).joinpath(marked_file_name)
        image.save(marked_file_path)
        return str(marked_file_path)

    @staticmethod
    def pretty_format_time(seconds: float) -> str:
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{seconds:05.2f}"
