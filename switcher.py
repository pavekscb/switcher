"""Автопереключатель раскладки (аналог Punto Switcher) для Windows.
Трей, автозапуск, ручное (Pause/Break) и автоматическое исправление."""
import ctypes
import io
import json
import math
import os
import random
import struct
import sys
import threading
import time
import traceback
import wave
import webbrowser
import winreg
import winsound
from ctypes import wintypes

import keyboard
import pystray
from PIL import Image, ImageDraw, ImageFont

from detector import should_fix
from layout import convert, detect_layout

APP_NAME = "LayoutSwitcher"
HOTKEY = "pause"
AUTO = True              # автоисправление при нажатии пробела/таба
SOUND = True             # тихий щелчок при исправлении
PROJECT_URL = "https://github.com/pavekscb/switcher"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.LoadKeyboardLayoutW.restype = ctypes.c_void_p
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetWindowThreadProcessId.restype = ctypes.c_uint
user32.GetKeyboardLayout.argtypes = [ctypes.c_uint]
user32.GetKeyboardLayout.restype = ctypes.c_void_p
user32.MapVirtualKeyExW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
user32.MapVirtualKeyExW.restype = ctypes.c_uint
user32.ToUnicodeEx.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.c_int, ctypes.c_uint, ctypes.c_void_p]
user32.ToUnicodeEx.restype = ctypes.c_int
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.GetGUIThreadInfo.argtypes = [ctypes.c_uint, ctypes.c_void_p]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("flags", ctypes.c_uint),
                ("hwndActive", ctypes.c_void_p), ("hwndFocus", ctypes.c_void_p),
                ("hwndCapture", ctypes.c_void_p), ("hwndMenuOwner", ctypes.c_void_p),
                ("hwndMoveSize", ctypes.c_void_p), ("hwndCaret", ctypes.c_void_p),
                ("rcCaret", wintypes.RECT)]

buffer: list[str] = []   # слово, которое печатается сейчас
last_word = ""           # последнее законченное слово
last_sep = ""            # разделитель после него (пробел/таб)
busy = False             # True, пока мы сами печатаем (игнорируем свои нажатия)


# ---------- звук и настройки ----------

CLICK_VOLUME = 0.22      # громкость щелчка (0..1)


def build_click() -> bytes:
    """Короткий сухой щелчок: шумовой импульс + едва слышный низкий «стук», WAV в памяти."""
    rate = 44100
    n = int(rate * 0.035)
    rng = random.Random(7)
    raw, lp = [], 0.0
    for i in range(n):
        t = i / rate
        lp += 0.15 * (rng.uniform(-1, 1) - lp)   # смягчённый шум: сухой «тик», а не шипение
        raw.append(lp * math.exp(-t / 0.0022) + 0.6 * math.sin(2 * math.pi * 200 * t) * math.exp(-t / 0.006))
    scale = CLICK_VOLUME / max(abs(v) for v in raw)
    frames = b"".join(struct.pack("<h", int(v * scale * 32767)) for v in raw)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return buf.getvalue()


CLICK = build_click()


def play_click():
    if SOUND:
        try:
            winsound.PlaySound(CLICK, winsound.SND_MEMORY)
        except Exception:
            pass


SETTINGS_FILE = os.path.join(os.environ.get("APPDATA", "."), APP_NAME, "settings.json")


def load_settings():
    global AUTO, SOUND
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        AUTO = bool(data.get("auto", AUTO))
        SOUND = bool(data.get("sound", SOUND))
    except (OSError, ValueError):
        pass


def save_settings():
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"auto": AUTO, "sound": SOUND}, f)
    except OSError:
        pass


# ---------- какую букву реально получит окно ----------

def window_hkl():
    """Раскладка потока, в который сейчас идёт ввод (окно с фокусом)."""
    hwnd = None
    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(info)
    if user32.GetGUIThreadInfo(0, ctypes.byref(info)):
        hwnd = info.hwndFocus or info.hwndActive
    if not hwnd:
        hwnd = user32.GetForegroundWindow()
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    return user32.GetKeyboardLayout(tid)


def key_char(scan_code: int, hkl) -> str:
    """Символ, который даст эта клавиша в раскладке hkl (с учётом Shift и CapsLock)."""
    vk = user32.MapVirtualKeyExW(scan_code, 1, hkl)  # MAPVK_VSC_TO_VK
    if not vk:
        return ""
    state = (ctypes.c_ubyte * 256)()
    if keyboard.is_pressed("shift"):
        state[0x10] = 0x80
    if user32.GetKeyState(0x14) & 1:
        state[0x14] = 1
    buf = ctypes.create_unicode_buffer(8)
    n = user32.ToUnicodeEx(vk, scan_code, state, buf, 8, 4, hkl)
    return buf.value[:n] if n == 1 else ""


# ---------- исправление ----------

def set_layout(target: str):
    """Переключить раскладку активного окна: 'ru' или 'en'."""
    klid = "00000419" if target == "ru" else "00000409"
    hkl = user32.LoadKeyboardLayoutW(klid, 1)
    user32.PostMessageW(user32.GetForegroundWindow(), 0x0050, 0, hkl)  # WM_INPUTLANGCHANGEREQUEST


def fix_last(expected: str | None = None):
    """expected — слово, которое хотел исправить автодетект (проверяем, что оно всё ещё последнее)."""
    global busy, last_word
    if expected is not None:
        if buffer or last_word != expected:
            return
        word, sep, from_buffer = last_word, last_sep, False
    elif buffer:
        word, sep, from_buffer = "".join(buffer), "", True
    elif last_word:
        word, sep, from_buffer = last_word, last_sep, False
    else:
        return

    src = detect_layout(word)
    if src == "unknown":
        return
    new = convert(word)

    busy = True
    try:
        for _ in range(len(word) + len(sep)):
            keyboard.send("backspace")
        set_layout("en" if src == "ru" else "ru")
        time.sleep(0.05)
        keyboard.write(new + sep)
        time.sleep(0.1)
    finally:
        busy = False

    threading.Thread(target=play_click, daemon=True).start()
    if from_buffer:
        buffer[:] = list(new)
    else:
        last_word = new
    print(f"исправлено: {word!r} -> {new!r}")


def auto_check(word: str, lang: int = 0):
    """Решение об автоисправлении — в отдельном потоке, чтобы не тормозить хук."""
    try:
        res = should_fix(word)
        print(f"авто: {word!r} [окно {lang:04x}] -> {'исправляю' if res else 'оставляю'}")
        if res:
            fix_last(expected=word)
    except Exception:
        traceback.print_exc()


def safe_fix():
    try:
        fix_last()
    except Exception:
        traceback.print_exc()


def on_key(e):
    global last_word, last_sep
    if busy or e.event_type != keyboard.KEY_DOWN:
        return

    name = e.name or ""

    if name == HOTKEY:
        threading.Thread(target=safe_fix, daemon=True).start()
        return

    if any(keyboard.is_pressed(k) for k in ("ctrl", "alt", "windows")):
        buffer.clear()
        last_word = ""
        return

    if name in ("space", "tab"):
        if buffer:
            last_word, last_sep = "".join(buffer), " " if name == "space" else "\t"
            buffer.clear()
            if AUTO:
                lang = (window_hkl() or 0) & 0xFFFF
                threading.Thread(target=auto_check, args=(last_word, lang), daemon=True).start()
    elif name == "enter":
        buffer.clear()
        last_word = ""
    elif name == "backspace":
        if buffer:
            buffer.pop()
        else:
            last_word = ""
    elif len(name) == 1:
        # символ берём не из имени клавиши keyboard, а по scan-коду в раскладке окна
        ch = name if e.is_keypad else (key_char(e.scan_code, window_hkl()) or name)
        buffer.append(ch)
        last_word = ""
    elif name in ("left", "right", "up", "down", "home", "end", "esc"):
        buffer.clear()
        last_word = ""


# ---------- автозапуск ----------

def autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return f'"{pyw}" "{os.path.abspath(__file__)}"'


def autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
        return True
    except OSError:
        return False


def set_autostart(on: bool):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except FileNotFoundError:
                pass


# ---------- трей ----------

def make_icon(active: bool) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, 62, 62), radius=14,
                        fill=(46, 160, 67, 255) if active else (130, 130, 130, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", 32)
    except OSError:
        font = ImageFont.load_default()
    d.text((8, 14), "Aя", font=font, fill="white")
    return img


def toggle_auto(icon, item):
    global AUTO
    AUTO = not AUTO
    icon.icon = make_icon(AUTO)
    save_settings()


def toggle_sound(icon, item):
    global SOUND
    SOUND = not SOUND
    save_settings()


def toggle_autostart(icon, item):
    set_autostart(not autostart_enabled())


def quit_app(icon, item):
    icon.stop()


# ---------- запуск ----------

def setup_streams():
    """Без консоли (exe): вывод слов отбрасываем, в лог пишем только ошибки."""
    if sys.stdout is None or getattr(sys, "frozen", False):
        sys.stdout = open(os.devnull, "w")
        log_dir = os.path.join(os.environ.get("APPDATA", "."), APP_NAME)
        os.makedirs(log_dir, exist_ok=True)
        sys.stderr = open(os.path.join(log_dir, "errors.log"), "a", encoding="utf-8", buffering=1)


def single_instance():
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, APP_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("Уже запущено.")
        sys.exit(0)


def warm_up():
    from wordfreq import zipf_frequency
    for lang in ("en", "ru", "uk"):
        zipf_frequency("test", lang)


def main():
    setup_streams()
    single_instance()
    load_settings()
    threading.Thread(target=warm_up, daemon=True).start()
    keyboard.hook(on_key)

    menu = pystray.Menu(
        pystray.MenuItem("Автоисправление", toggle_auto, checked=lambda i: AUTO, default=True),
        pystray.MenuItem("Звук переключения", toggle_sound, checked=lambda i: SOUND),
        pystray.MenuItem("Автозапуск с Windows", toggle_autostart, checked=lambda i: autostart_enabled()),
        pystray.MenuItem("Проект на GitHub", lambda icon, item: webbrowser.open(PROJECT_URL)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Выход", quit_app),
    )
    icon = pystray.Icon(APP_NAME, make_icon(AUTO),
                        "Раскладка: авто вкл. Pause — исправить вручную", menu)
    print("Работает (иконка в трее). Pause — исправить вручную. Выход: меню в трее.")
    icon.run()
    keyboard.unhook_all()


if __name__ == "__main__":
    main()
