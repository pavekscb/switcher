# main.py
import keyboard 
import time
import pyperclip
# Импорт ВСЕХ необходимых функций из наших модулей
from converter import EN_TO_RU_MAP, RU_TO_EN_MAP, convert_text
from system_utils import switch_keyboard_layout, set_autostart, is_autostart_enabled 
from gui_manager import setup_tray_icon, open_about_window
from input_sim import simulate_press_release, kb_controller
from pynput.keyboard import Key 


# --- ГЛОБАЛЬНЫЙ БУФЕР ДЛЯ АВТООТКАТА ---
# Хранит все символы в их нейтральном (латинском) представлении
typed_keys_buffer = [] 
# ----------------------------------------


def fix_and_replace_word_new(word_to_fix):
    """
    Конвертирует слово, удаляет его с экрана и вставляет новое.
    Используется узкоспециализированная логика для определения целевого языка.
    """
    
    # --- 1. ЛОГИКА ОПРЕДЕЛЕНИЯ ЦЕЛЕВОГО ЯЗЫКА (Финальная эвристика) ---
    
    word_lower = word_to_fix.lower()
    is_intended_english_target = False
    
    # Мы ищем только очень специфичные маркеры, чтобы избежать ложных срабатываний 
    # на обычных русских словах типа 'rbyj' (кино) или 'ghbdtn' (привет).
    
    # 1. Проверка на английские слова с уникальными маркерами ('hello', 'world', 'is')
    if any(char in word_lower for char in 'loi'): 
        is_intended_english_target = True
    
    # 2. Узкая проверка на 'try' (буфер: ekh) и 'key' (буфер: rdu)
    # Используем комбинацию символов, а не просто отдельные буквы
    elif (len(word_to_fix) in (3, 4) and 
          (('e' in word_lower and 'k' in word_lower) or  # для 'try' (ekh)
           ('r' in word_lower and 'd' in word_lower))): # для 'key' (rdu)
        is_intended_english_target = True
        
    
    if is_intended_english_target:
        # Случай 2: РУССКИЙ НАБОР С АНГЛИЙСКИМ НАМЕРЕНИЕМ. Цель: ЛАТИНИЦА (екн -> try)
        # Двойная конвертация: (ekh -> екн) -> (try)
        word_in_cyrillic = convert_text(word_to_fix, EN_TO_RU_MAP)
        new_word = convert_text(word_in_cyrillic, RU_TO_EN_MAP)
        
    else:
        # Случай 1: АНГЛИЙСКИЙ НАБОР С РУССКИМ НАМЕРЕНИЕМ. Цель: КИРИЛЛИЦА (ghbdtn -> привет)
        # Одинарная конвертация: (ghbdtn) -> (привет)
        new_word = convert_text(word_to_fix, EN_TO_RU_MAP)

    
    # --- 2. УДАЛЕНИЕ И ВСТАВКА ---
    word_length = len(word_to_fix)
    
    try:
        # 1. Удаляем слово
        for _ in range(word_length): 
            simulate_press_release(Key.backspace)
            # Задержка 0.02s взята из input_sim.py
            
        # 2. Вставляем новое слово
        kb_controller.type(new_word) 
        time.sleep(0.15) # УВЕЛИЧЕННАЯ ЗАДЕРЖКА ДЛЯ СТАБИЛЬНОСТИ
        
        # 3. Переключаем раскладку
        switch_keyboard_layout()
        time.sleep(0.1) # ДОПОЛНИТЕЛЬНАЯ ЗАДЕРЖКА
        
        print(f"Исправлено: '{word_to_fix}' -> '{new_word}' (Автооткат)")
        
    except Exception as e:
        print(f"Критическая ошибка при вводе: {e}")
    

def keyboard_callback(event):
    """
    Обработчик, который собирает слово в нейтральном (латинском) буфере и ждет Scroll Lock.
    """
    global typed_keys_buffer

    if event.event_type == keyboard.KEY_DOWN:
        key_name = event.name
        
        # 1. Если нажата наша горячая клавиша (Scroll Lock)
        if key_name == 'scroll lock':
            if typed_keys_buffer:
                word_to_fix = "".join(typed_keys_buffer)
                fix_and_replace_word_new(word_to_fix) 
                typed_keys_buffer = [] 
            return True 

        # 2. Если нажата клавиша-разделитель (пробел, Enter, Tab)
        elif key_name in ('space', 'enter', 'tab'):
            typed_keys_buffer = [] 
            
        # 3. Если нажата Backspace
        elif key_name == 'backspace':
            if typed_keys_buffer:
                typed_keys_buffer.pop() 
            
        # 4. Если нажата обычная буква (только символы длиной 1)
        elif len(key_name) == 1:
            # Преобразуем кириллический ввод в латинский (нейтральный) для хранения.
            is_cyrillic = key_name in 'йцукенгшщзхъфывапролджэячсмитьбюёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ'
            if is_cyrillic:
                neutral_key = RU_TO_EN_MAP.get(key_name, key_name)
            else:
                neutral_key = key_name

            typed_keys_buffer.append(neutral_key)
            
    return False 


def main():
    """Основная точка входа в программу."""
    
    # --- ВКЛЮЧЕНИЕ АВТОЗАПУСКА ПО УМОЛЧАНИЮ ---
    if not is_autostart_enabled():
        success, message = set_autostart(True)
        if success:
            print(f"Инициализация: {message}")
    
    def on_exit(icon, item):
        keyboard.unhook_all()
        icon.stop()

    icon = setup_tray_icon(on_exit, lambda icon, item: open_about_window(icon, item))
    if icon is None:
        print("Не удалось запустить трей. Выход.")
        return

    keyboard.hook(keyboard_callback) 
    print("Программа запущена в трее. Активирован автооткат по Scroll Lock.")
    icon.run() 
    print("Программа завершена.")

if __name__ == '__main__':
    main()
