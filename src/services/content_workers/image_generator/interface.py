from abc import ABC, abstractmethod

from PIL import Image


class IImageGenerator(ABC):
    @abstractmethod
    def generate(self, base64_image_str: str, text: str) -> Image.Image:
        """Принимает base64 и текст, возвращает объект PIL Image"""
        pass

    @abstractmethod
    def generate_from_url(self, image_url: str, text: str) -> Image.Image:
        """Принимает URL изображения и текст, возвращает объект PIL Image"""
        pass
