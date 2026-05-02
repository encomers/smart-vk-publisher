import base64
import io
import re

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
    ImageStat,
)

from src.utils import to_base64_image

from .interface import IImageGenerator


class ImageOverlayGenerator(IImageGenerator):
    def __init__(
        self,
        overlay_light_path: str,
        overlay_dark_path: str,
        font_path: str,
        font_size: int,
        blur_radius: int = 5,
        darkness_factor: float = 0.7,
    ):
        """
        :param overlay_light_path: Путь к PNG для светлых фото (под черный текст)
        :param overlay_dark_path: Путь к PNG для темных фото (под белый текст)
        :param font_path: Путь к .ttf или .otf файлу шрифта
        :param font_size: Размер шрифта
        :param blur_radius: Сила размытия по Гауссу (0 - без размытия)
        :param darkness_factor: Яркость фона (1.0 - оригинал, < 1.0 - темнее)
        """
        self.overlay_light = Image.open(overlay_light_path).convert("RGBA")
        self.overlay_dark = Image.open(overlay_dark_path).convert("RGBA")
        self.font = ImageFont.truetype(font_path, font_size)
        self.blur_radius = blur_radius
        self.darkness_factor = darkness_factor

    def _is_dark(self, img: Image.Image) -> bool:
        """
        Определяет среднюю яркость изображения.
        Возвращает True, если изображение темное.
        """
        # Конвертируем в Grayscale (L) для анализа светимости
        stat = ImageStat.Stat(img.convert("L"))
        average_brightness = stat.mean[0]
        # 127 — это середина шкалы 0-255
        return average_brightness < 127

    def _apply_typography(self, text: str) -> str:
        """
        Склеивает предлоги, союзы и числа с помощью неразрывных пробелов.
        """
        nbsp = "\u00a0"

        # Склеиваем блоки цифр (1 000 000)
        text = re.sub(r"(?<=\d)\s+(?=\d)", nbsp, text)

        # Склеиваем число и следующее слово (10 кг, 2024 год)
        text = re.sub(r"(^|\s)(\d+)\s+", f"\\1\\2{nbsp}", text)

        # Привязываем тире
        text = re.sub(r"\s+(—|-)", f"{nbsp}\\1", text)

        # Привязываем короткие слова (до 3 букв включительно)
        prev_text = ""
        while text != prev_text:
            prev_text = text
            text = re.sub(
                r"(?i)(^|\s)([a-zA-Zа-яА-ЯёЁ]{1,3})\s+", f"\\1\\2{nbsp}", text
            )

        return text

    def _smart_wrap(self, text: str, draw: ImageDraw.ImageDraw, max_width: int) -> str:
        """
        Разбивает текст на строки с учетом ширины и правил типографики.
        """
        text = self._apply_typography(text)
        words = re.split(r" +", text)

        lines: list[str] = []
        current_line = []

        for word in words:
            # Для замера ширины заменяем неразрывный пробел обратно на обычный
            test_line = " ".join(current_line + [word]).replace("\u00a0", " ")
            width = draw.textlength(test_line, font=self.font)

            if width <= max_width or not current_line:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line).replace("\u00a0", " "))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line).replace("\u00a0", " "))

        return "\n".join(lines)

    def generate(self, base64_image_str: str, text: str) -> str:
        """
        Основной цикл генерации изображения.
        """
        # Декодирование base64
        if "," in base64_image_str:
            base64_image_str = base64_image_str.split(",")[1]
        image_data = base64.b64decode(base64_image_str)
        base_img = Image.open(io.BytesIO(image_data)).convert("RGBA")

        # 1. Проверяем яркость оригинала для выбора темы
        dark_mode = self._is_dark(base_img)

        if dark_mode:
            current_overlay = self.overlay_dark
            text_color = (255, 255, 255, 255)  # Белый текст
        else:
            current_overlay = self.overlay_light
            text_color = (0, 0, 0, 255)  # Черный текст

        overlay_w, overlay_h = current_overlay.size

        # 2. Подготовка фонового изображения
        base_img = ImageOps.fit(
            base_img,
            (overlay_w, overlay_h),
            method=Image.Resampling.LANCZOS,
        )  # type: ignore

        # Применяем размытие
        if self.blur_radius > 0:
            base_img = base_img.filter(
                ImageFilter.GaussianBlur(radius=self.blur_radius)
            )

        # Применяем затемнение
        enhancer = ImageEnhance.Brightness(base_img)
        base_img = enhancer.enhance(self.darkness_factor)

        # 3. Сборка композиции
        canvas = Image.new("RGBA", (overlay_w, overlay_h), (0, 0, 0, 0))

        # Вставляем фото со сдвигом 60px
        canvas.paste(base_img, (60, 0))

        # Накладываем выбранный оверлей
        canvas.alpha_composite(current_overlay)

        # 4. Рендеринг текста
        draw = ImageDraw.Draw(canvas)
        left_padding = 50
        right_padding = 50

        text_width_koeff = 3 / 4

        max_text_width = (
            int(overlay_w * text_width_koeff) - left_padding - right_padding
        )  # Максимальная ширина текста - 3/4 от ширины изображения

        wrapped_text = self._smart_wrap(text, draw, max_text_width)

        # Вычисляем высоту текстового блока для центрирования по Y
        bbox = draw.multiline_textbbox(
            (0, 0),
            wrapped_text,
            font=self.font,
            spacing=4,
        )
        text_height = bbox[3] - bbox[1]
        y_pos = (overlay_h - text_height) // 2

        draw.multiline_text(
            (left_padding, y_pos),
            wrapped_text,
            font=self.font,
            fill=text_color,
            align="left",
            spacing=4,
        )

        return self._to_base64(canvas)

    async def generate_from_url(self, image_url: str, text: str) -> str:
        try:
            img: str = await to_base64_image(image_url)
        except Exception as e:
            raise ValueError(f"Error occurred while fetching image from URL: {e}")
        return self.generate(img, text)

    def _to_base64(self, img: Image.Image) -> str:
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
