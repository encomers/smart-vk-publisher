from abc import ABC, abstractmethod

from PIL import Image


class IImageGenerator(ABC):
    @abstractmethod
    def generate(self, base64_image_str: str, text: str) -> Image.Image:
        """Принимает base64 и текст, возвращает объект PIL Image"""
        pass
