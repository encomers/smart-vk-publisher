import base64
import io
import re

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


class ImageOverlayGenerator:
    def __init__(
        self,
        overlay_path: str,
        font_path: str,
        font_size: int,
        blur_radius: int = 5,
        darkness_factor: float = 0.7,
    ):
        """
        :param overlay_path: Путь к оверлею.
        :param font_path: Путь к шрифту.
        :param font_size: Размер шрифта.
        :param blur_radius: Радиус размытия по Гауссу (чем больше, тем сильнее размытие).
        :param darkness_factor: Коэффициент яркости (1.0 — без изменений, 0.0 — черный экран).
        """
        self.overlay = Image.open(overlay_path).convert("RGBA")
        self.font = ImageFont.truetype(font_path, font_size)
        self.font_size = font_size
        self.blur_radius = blur_radius
        self.darkness_factor = darkness_factor

    def _apply_typography(self, text: str) -> str:
        nbsp = "\u00a0"
        text = re.sub(r"(?<=\d)\s+(?=\d)", nbsp, text)
        text = re.sub(r"(^|\s)(\d+)\s+", f"\\1\\2{nbsp}", text)
        text = re.sub(r"\s+(—|-)", f"{nbsp}\\1", text)
        prev_text = ""
        while text != prev_text:
            prev_text = text
            text = re.sub(
                r"(?i)(^|\s)([a-zA-Zа-яА-ЯёЁ]{1,3})\s+", f"\\1\\2{nbsp}", text
            )
        return text

    def _smart_wrap(self, text: str, draw: ImageDraw.ImageDraw, max_width: int) -> str:
        text = self._apply_typography(text)
        words = [w for w in text.split(" ") if w]
        lines: list[str] = []
        current_line = []

        for word in words:
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

    def generate(self, base64_image_str: str, text: str) -> Image.Image:
        if "," in base64_image_str:
            base64_image_str = base64_image_str.split(",")[1]

        image_data = base64.b64decode(base64_image_str)
        base_img = Image.open(io.BytesIO(image_data)).convert("RGBA")

        overlay_w, overlay_h = self.overlay.size

        # 1. Масштабируем
        base_img = base_img.resize((overlay_w, overlay_h), Image.Resampling.LANCZOS)

        # 2. Размываем по Гауссу
        if self.blur_radius > 0:
            base_img = base_img.filter(
                ImageFilter.GaussianBlur(radius=self.blur_radius)
            )

        # 3. Затемняем
        # Используем ImageEnhance для управления яркостью
        enhancer = ImageEnhance.Brightness(base_img)
        base_img = enhancer.enhance(self.darkness_factor)

        # Создаем холст
        canvas = Image.new("RGBA", (overlay_w, overlay_h), (0, 0, 0, 0))

        # Накладываем обработанное фото со сдвигом 60px
        canvas.paste(base_img, (60, 0))

        # Накладываем оверлей
        canvas.alpha_composite(self.overlay)

        # Отрисовка текста
        draw = ImageDraw.Draw(canvas)
        max_text_width = overlay_w - 20
        wrapped_text = self._smart_wrap(text, draw, max_text_width)

        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=self.font)
        text_height = bbox[3] - bbox[1]
        y_pos = (overlay_h - text_height) // 2

        draw.multiline_text(
            (50, y_pos),
            wrapped_text,
            font=self.font,
            fill=(255, 255, 255, 255),
            align="left",
            spacing=4,
        )

        return canvas
