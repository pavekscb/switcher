# gui_manager.py
import pystray
# Импортируем ImageFont для работы с TrueType шрифтами
from PIL import Image, ImageDraw, ImageFont 
import tkinter as tk
import os
import webbrowser
from system_utils import is_autostart_enabled, set_autostart, APP_NAME 


# --- НАСТРОЙКА ШРИФТА ДЛЯ ИКОНКИ ТРЕЯ ---
FONT_PATH = "C:/Windows/Fonts/arial.ttf" # Путь к стандартному шрифту Windows
FONT_SIZE = 30 # <-- УМЕНЬШЕНО: Размер текста
# -----------------------------------------

try:
    # Загружаем TrueType шрифт
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
except Exception:
    # Если файл не найден (на другой ОС или отсутствует), используем шрифт по умолчанию
    font = ImageFont.load_default()
    print("Внимание: TrueType шрифт не найден. Используется шрифт по умолчанию.")


ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.png") 
GITHUB_URL = "https://github.com/ваш_логин/ваш_репозиторий" 


def open_about_window(icon, item):
    """Открывает окно с информацией о программе и ссылкой на GitHub в центре экрана."""
    root = tk.Tk()
    root.title(f"О программе {APP_NAME}")
    
    # 1. Задаем размеры окна
    WINDOW_WIDTH = 450 
    WINDOW_HEIGHT = 220 
    
    # 2. Получаем размеры экрана и рассчитываем позицию
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - WINDOW_WIDTH/2)
    center_y = int(screen_height/2 - WINDOW_HEIGHT/2)
    
    # 3. Устанавливаем геометрию (размер и позиция)
    root.geometry(f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{center_x}+{center_y}')
    
    
    # --- ИСПОЛЬЗОВАНИЕ ФРЕЙМА ДЛЯ ГАРАНТИРОВАННОГО ОТСТУПА ---
    
    # Создаем основной фрейм для отступов
    main_frame = tk.Frame(root, padx=20, pady=10) 
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 1. Заголовок (Simple Switcher)
    label_title = tk.Label(main_frame, 
                           text="Simple Switcher (Автопереключатель раскладки)", 
                           justify=tk.LEFT, 
                           anchor='w', 
                           font=('TkDefaultFont', 10, 'bold')) 
    label_title.pack(fill=tk.X, pady=(0, 10)) 

    # 2. Детали
    info_text_details = (
        "Горячая клавиша: Scroll Lock\n"
        "Назначение: Автоматический откат последнего слова и переключение раскладки."
    )
    
    label_details = tk.Label(main_frame, 
                             text=info_text_details, 
                             justify=tk.LEFT,
                             anchor='w') 
    label_details.pack(fill=tk.X, pady=(0, 15))

    # Ссылка на GitHub
    link = tk.Label(main_frame, text=f"Код на GitHub: {GITHUB_URL}", fg="blue", cursor="hand2")
    link.pack(pady=5)
    
    def callback(url):
        webbrowser.open_new_tab(url)
        
    link.bind("<Button-1>", lambda e: callback(GITHUB_URL))
    
    close_button = tk.Button(main_frame, text="Закрыть", command=root.destroy)
    close_button.pack(pady=10)
    
    root.mainloop()


def toggle_autostart(icon, item):
    """Обработчик, который переключает статус автозапуска и обновляет меню."""
    current_state = is_autostart_enabled()
    success, message = set_autostart(not current_state)
    
    if success:
        print(message)
        icon.update_menu() 
    else:
        print(f"Ошибка при переключении автозапуска: {message}")


def setup_tray_icon(on_exit_callback, on_about_callback):
    """
    Настраивает и запускает значок в системном трее, используя ДИНАМИЧЕСКИ ГЕНЕРИРУЕМОЕ ИЗОБРАЖЕНИЕ.
    """
    try:
        # --- БЛОК ГЕНЕРАЦИИ ИКОНКИ: Светло-голубой цвет (#87CEFA) и буквы 'SW' ---
        image = Image.new('RGB', (64, 64), '#87CEFA') 
        d = ImageDraw.Draw(image)
        
        # Используем загруженный TrueType шрифт (размер 30)
        d.text((10, 15), 'SW', fill='black', font=font) 
        # ------------------------------------------------------------------------------------
        
        
        # Функция, которая будет динамически генерировать пункты меню
        def create_menu():
            is_checked = is_autostart_enabled()
            
            # --- Динамическое меню ---
            return (
            pystray.MenuItem('О программе', on_about_callback, default=True), 
            pystray.MenuItem(
                'Автозапуск', 
                toggle_autostart,
                checked=lambda item: is_autostart_enabled()
            ),
            pystray.MenuItem('Выход', on_exit_callback)
            )
        
        icon = pystray.Icon("simple_switcher", image, "Simple Switcher", menu=pystray.Menu(create_menu))
        
        return icon

    except Exception as e:
        print(f"Ошибка при настройке трея: {e}")
        return None
