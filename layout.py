"""Конвертер раскладок EN (QWERTY) <-> RU (ЙЦУКЕН). Шаг 1."""

EN_LOW = "`qwertyuiop[]asdfghjkl;'zxcvbnm,./"
RU_LOW = "ёйцукенгшщзхъфывапролджэячсмитьбю."

EN_UP = '~QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?'
RU_UP = RU_LOW.upper()[:-1] + ","

# Shift + цифры: в RU-раскладке другие символы
EN_NUM = '@#$^&'
RU_NUM = '"№;:?'

_en = EN_LOW + EN_UP + EN_NUM
_ru = RU_LOW + RU_UP + RU_NUM

EN2RU = dict(zip(_en, _ru))
RU2EN = dict(zip(_ru, _en))


def _is_cyr(ch: str) -> bool:
    return "а" <= ch.lower() <= "я" or ch.lower() == "ё"


def _is_lat(ch: str) -> bool:
    return "a" <= ch.lower() <= "z"


def detect_layout(text: str) -> str:
    """Возвращает 'ru', 'en' или 'unknown' по буквам в тексте."""
    cyr = sum(_is_cyr(c) for c in text)
    lat = sum(_is_lat(c) for c in text)
    if cyr > lat:
        return "ru"
    if lat > cyr:
        return "en"
    return "unknown"


def convert(text: str, direction: str | None = None) -> str:
    """
    direction: 'en2ru', 'ru2en' или None (определить автоматически).
    Неизвестные символы остаются как есть.
    """
    if direction is None:
        layout = detect_layout(text)
        if layout == "unknown":
            return text
        direction = "ru2en" if layout == "ru" else "en2ru"
    table = EN2RU if direction == "en2ru" else RU2EN
    return "".join(table.get(c, c) for c in text)


if __name__ == "__main__":
    assert convert("ghbdtn") == "привет"
    assert convert("Ghbdtn") == "Привет"
    assert convert("ghbdtn,") == "приветб"  # запятая = клавиша Б
    assert convert("руддщ") == "hello"
    assert convert("Руддщ") == "Hello"
    assert convert("ghbdtn", "en2ru") == "привет"
    assert convert("ЙЦУКЕН") == "QWERTY"
    assert convert("123 !") == "123 !"
    assert convert("") == ""
    assert convert("ntrcn&") == "текст?"
    assert convert("ntrcn?") == "текст,"
    assert convert("`", "en2ru") == "ё"
    # круговое преобразование
    s = "Hello, World! [test] {ok}; 'q' \"z\""
    assert convert(convert(s, "en2ru"), "ru2en") == s
    print("Все тесты прошли")
