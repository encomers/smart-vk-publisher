from abc import ABC, abstractmethod

from PIL import Image


class IImageGenerator(ABC):
    @abstractmethod
    def generate(self, base64_image_str: str, text: str) -> Image.Image:
        """Принимает base64 и текст, возвращает объект PIL Image"""
        pass

    @abstractmethod
    async def generate_from_url(self, image_url: str, text: str) -> Image.Image:
        """Принимает URL изображения и текст, возвращает объект PIL Image"""
        pass

    @abstractmethod
    def to_base64(self, img: Image.Image) -> str:
        """Принимает объект PIL Image, возвращает строку в формате base64"""
        pass
