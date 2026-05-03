import re

from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # 1. Удаляем мусорные теги целиком
    for tag in soup.find_all(["figure", "script", "style", "head"]):
        tag.decompose()

    # 2. Обработка списков (только прямые дочерние <li>)
    for ul in soup.find_all("ul"):
        items = [
            f"* {li.get_text(strip=True)}" for li in ul.find_all("li", recursive=False)
        ]
        ul.replace_with("\n".join(items))

    for ol in soup.find_all("ol"):
        items = [
            f"{i}. {li.get_text(strip=True)}"
            for i, li in enumerate(ol.find_all("li", recursive=False), 1)
        ]
        ol.replace_with("\n".join(items))

    # 3. <br> → двойной перенос
    for br in soup.find_all("br"):
        br.replace_with("\n\n")

    # 4. Извлекаем текст без лишнего separator
    text = soup.get_text()

    # 5. Чистим пробелы
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
