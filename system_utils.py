# system_utils.py
import ctypes
import winreg
import sys
import os
import time

# --- Windows API для переключения раскладки ---
HWND_BROADCAST = 0xFFFF
WM_INPUTLANGCHANGEREQUEST = 0x0050

def switch_keyboard_layout():
    """Переключает текущую раскладку клавиатуры, отправляя сообщение WM_INPUTLANGCHANGEREQUEST."""
    try:
        ctypes.windll.user32.PostMessageA(
            HWND_BROADCAST,
            WM_INPUTLANGCHANGEREQUEST,
            0,
            0
        )
        time.sleep(0.05)
        return True
    except Exception as e:
        print(f"Ошибка при переключении раскладки: {e}")
        return False

# --- Автозапуск Windows ---

APP_NAME = "SimpleSwitcher"
REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_exe_path():
    """Получает путь к текущему исполняемому файлу."""
    return os.path.abspath(sys.argv[0])

def is_autostart_enabled(app_name=APP_NAME):
    """Проверяет, включен ли автозапуск."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        # Если ключ существует, автозапуск включен
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def set_autostart(enable: bool, app_name=APP_NAME):
    """Включает или выключает автозапуск Windows."""
    try:
        if enable:
            exe_path = get_exe_path()
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE)
            path_with_quotes = f'"{exe_path}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, path_with_quotes)
            winreg.CloseKey(key)
            return True, f"Автозапуск для {app_name} включен."
        else:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, app_name)
            winreg.CloseKey(key)
            return True, f"Автозапуск для {app_name} отключен."
    except FileNotFoundError:
        # Пытаемся удалить несуществующий ключ - это нормально
        if not enable:
             return True, f"Автозапуск уже отключен."
        return False, f"Ошибка: не найден путь реестра."
    except Exception as e:
        return False, f"Ошибка при изменении автозапуска: {e}"
