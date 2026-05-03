from abc import ABC, abstractmethod


class IImageGenerator(ABC):
    @abstractmethod
    def generate(self, base64_image_str: str, text: str) -> str:
        """Принимает base64 и текст, возвращает объект PIL Image"""
        pass

    @abstractmethod
    async def generate_from_url(self, image_url: str, text: str) -> str:
        """Принимает URL изображения и текст, возвращает объект PIL Image"""
        pass
