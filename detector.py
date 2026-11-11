"""Шаг 4: решаем, набрано ли слово не в той раскладке (словарь wordfreq)."""
from wordfreq import zipf_frequency
from layout import convert, detect_layout

MIN_LEN = 2          # однобуквенные не трогаем
TARGET_MIN = 3.0     # в нужной раскладке слово должно быть достаточно частым
GAP = 2.0            # и частота должна быть выше минимум на столько
RARE_LEN = 6            # длинное слово, которого нет в словаре исходной раскладки,
RARE_TARGET_MIN = 2.0    # можно исправлять и по более редкому слову в другой раскладке
SHORT_TARGET_MIN = 6.0   # для 2-буквенных слов порог строже:
SHORT_GAP = 2.5          # и быть заметно частотнее, чем как набрано


def should_fix(word: str) -> bool:
    if len(word) < MIN_LEN or not any(c.isalpha() for c in word):
        return False
    src = detect_layout(word)
    if src == "unknown":
        return False
    dst = "en" if src == "ru" else "ru"
    src_lang = "ru" if src == "ru" else "en"
    src_f = zipf_frequency(word, src_lang)
    if src_lang == "ru":
        src_f = max(src_f, zipf_frequency(word, "uk"))
    if any(c in word for c in "`[];"):
        src_f = 0.0   # такие клавиши в нормальном английском слове не встречаются
    dst_f = zipf_frequency(convert(word), dst)
    # в нужной раскладке слово частое и заметно «лучше», чем как набрано
    if len(word) == 2:
        if not convert(word).isalpha():
            return False
        if src_lang == "ru" and src_f >= 2.0:   # «ща», «ага» и т.п. — реальные слова
            return False
        return dst_f >= SHORT_TARGET_MIN and dst_f - src_f >= SHORT_GAP
    min_dst = TARGET_MIN
    if src_f == 0 and len(word) >= RARE_LEN:
        min_dst = RARE_TARGET_MIN
    return dst_f >= min_dst and dst_f - src_f >= GAP


if __name__ == "__main__":
    yes = ["ghbdtn", "gjrf", "rfr", "ntrcn", "'nj", "cgfcb,j", "руддщ", "цщкв", "вфеф", "ьфлу"]
    no = ["hello", "привет", "world", "python", "github", "ok", "кот", "hi", "україна", "kubectl", "http"]
    bad = [w for w in yes if not should_fix(w)] + [w for w in no if should_fix(w)]
    for w in yes + no:
        print(f"{w:10} {str(should_fix(w)):6} -> {convert(w)}")
    print("ОШИБКИ:", bad or "нет")
