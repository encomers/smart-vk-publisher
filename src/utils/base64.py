import base64

import httpx


async def to_base64_image(url: str) -> str:
    """Скачивает изображение по URL и возвращает его в виде строки в формате data URI (base64).

    Args:
        url (str): Ссылка на изображение, которое нужно скачать и преобразовать.

    Returns:
        str: Валидная строка в формате data URI, содержащая изображение в виде base64.
    """
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        r.raise_for_status()

    content_type = r.headers.get("content-type", "image/jpeg")

    b64 = base64.b64encode(r.content).decode("utf-8")
    return f"data:{content_type};base64,{b64}"
