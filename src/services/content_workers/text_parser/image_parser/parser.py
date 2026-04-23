import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import HttpUrl, ValidationError

from .interface import IImageParser

logger = logging.getLogger(__name__)

BASE_URL = "https://realnoevremya.ru"


class ImageParser(IImageParser):
    def get_images(self, text: str) -> list[HttpUrl] | None:
        soup = BeautifulSoup(text, "lxml")

        images = soup.find_all("img")
        img_list: list[HttpUrl] = []

        for image in images:
            src = image.get("src")
            if not isinstance(src, str) or not src.strip():
                logger.warning(f"Image tag found without valid src attribute: {image}")
                continue

            if "/uploads/mediateka/" not in src:
                continue

            try:
                url = urljoin(BASE_URL, src)
                img_list.append(HttpUrl(url))
            except ValidationError as e:
                logger.warning(
                    f"Failed to create HttpUrl for image src: {src}, error: {e}"
                )

        return img_list or None
