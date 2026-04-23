def replace_first_line(text: str, new_line: str) -> str:
    """Заменяет первую строку текста на переданную new_line."""
    # partition разбивает строку по первому вхождению '\n'
    # Возвращает кортеж: (до_разделителя, сам_разделитель, после_разделителя)
    _, sep, tail = text.partition("\n")
    return new_line + sep + tail
