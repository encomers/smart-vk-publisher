import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import HttpUrl, ValidationError

from .interface import IImageParser

logger = logging.getLogger(__name__)

# Базовый URL для преобразования относительных ссылок в абсолютные
BASE_URL = "https://realnoevremya.ru"


class ImageParser(IImageParser):
    """
    Реализация парсера изображений, ориентированная на структуру сайта RealnoeVremya.

    Использует BeautifulSoup для поиска тегов <img> и фильтрует их, оставляя только те,
    которые относятся к официальной медиатеке сайта.
    """

    def get_images(self, text: str) -> list[HttpUrl] | None:
        """
        Извлекает список URL-адресов изображений из HTML-строки.

        Логика работы:
        1. Парсит входящий текст как HTML с помощью 'lxml'.
        2. Ищет все теги <img>.
        3. Проверяет наличие атрибута 'src'.
        4. Фильтрует изображения, оставляя только те, чей путь содержит '/uploads/mediateka/'.
        5. Превращает относительные ссылки в абсолютные, используя BASE_URL.
        6. Валидирует результат через Pydantic HttpUrl.

        Args:
            text (str): HTML-код или текст, из которого нужно извлечь картинки.

        Returns:
            list[HttpUrl] | None: Список валидных URL или None, если подходящих
                                  изображений не найдено.
        """
        # Создание объекта BeautifulSoup для эффективного поиска по DOM
        soup = BeautifulSoup(text, "lxml")

        images = soup.find_all("img")
        img_list: list[HttpUrl] = []

        for image in images:
            src = image.get("src")

            # Проверка: является ли src строкой и не пуста ли она
            if not isinstance(src, str) or not src.strip():
                logger.warning(f"Image tag found without valid src attribute: {image}")
                continue

            # Фильтрация: берем только изображения из папки медиатеки
            if "/uploads/mediateka/" not in src:
                continue

            try:
                # Склеиваем домен и путь (например, /uploads/... -> https://site.ru/uploads/...)
                url = urljoin(BASE_URL, src)
                img_list.append(HttpUrl(url))
            except ValidationError as e:
                logger.warning(
                    f"Failed to create HttpUrl for image src: {src}, error: {e}"
                )

        return img_list or None
