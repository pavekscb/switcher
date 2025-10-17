# input_sim.py
import time
from pynput.keyboard import Controller, Key

# Инициализация контроллера pynput
kb_controller = Controller()

def simulate_press_release(key):
    """Имитирует нажатие и отпускание клавиши."""
    kb_controller.press(key)
    kb_controller.release(key)
    # УВЕЛИЧЕННАЯ ЗАДЕРЖКА для лучшей стабильности
    time.sleep(0.02)
