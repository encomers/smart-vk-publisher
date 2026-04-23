from abc import ABC, abstractmethod

from pydantic import HttpUrl


class IImageParser(ABC):
    """
    Интерфейс для извлечения URL-адресов изображений из текстового контента.

    Обеспечивает абстракцию над методами поиска изображений (например,
    через регулярные выражения, парсинг HTML/BeautifulSoup или внешние API).
    """

    @abstractmethod
    def get_images(self, text: str) -> list[HttpUrl] | None:
        """
        Выполняет поиск и сбор всех ссылок на изображения в переданном тексте.

        Args:
            text (str): Строка, в которой необходимо произвести поиск
                        (может содержать HTML-теги или plain text).

        Returns:
            list[HttpUrl] | None: Список валидных объектов HttpUrl, если изображения найдены.
                                  Возвращает None, если изображений нет или текст пуст.

        Example:
            >>> parser.get_images('<img src="https://example.com/pic.jpg">')
            [HttpUrl('https://example.com/pic.jpg')]
        """
        ...
