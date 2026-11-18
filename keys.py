"""Таблица управления: какая клавиша какое действие означает.

Windows присылает в событии Tk две вещи:

* ``keysym`` — символ, и он зависит от раскладки. На русской раскладке
  клавиша R приходит как ``Cyrillic_ka``, поэтому проверка по букве «r»
  перестаёт работать — именно из-за этого «к» не перезапускала игру;
* ``keycode`` — виртуальный код клавиши (VK_* в Windows). Он одинаков
  для любой раскладки: физическая клавиша R всегда даёт 82.

Поэтому действие сначала ищется по ``keycode``, а ``keysym`` — запасной
путь для систем, где коды другие (и просто чтобы таблица читалась).

Модуль не импортирует tkinter, поэтому таблицу можно проверить тестами
без открытия окна — см. test_keys.py.
"""

LEFT = "left"           # шаг головы влево
RIGHT = "right"         # шаг головы вправо
DOWN = "down"           # ускоренное падение, пока клавиша зажата
DROP = "drop"           # мгновенный сброс до упора
PAUSE = "pause"         # пауза и снятие с паузы
RESTART = "restart"     # начать заново в любой момент
CONFIRM = "confirm"     # начать заново после Game Over

# Сложность: 1, 2, 3 (и те же цифры на цифровом блоке).
EASY = "easy"
NORMAL = "normal"
HARD = "hard"
DIFFICULTY_ACTIONS = (EASY, NORMAL, HARD)

# Виртуальные коды клавиш Windows (VK_*).
BY_KEYCODE = {
    37: LEFT, 39: RIGHT, 40: DOWN, 38: DROP,    # ← → ↓ ↑
    65: LEFT, 68: RIGHT, 83: DOWN, 87: DROP,    # A D S W
    32: DROP,                                   # пробел
    27: PAUSE, 80: PAUSE,                       # Esc, P
    82: RESTART,                                # R
    13: CONFIRM,                                # Enter
    49: EASY, 50: NORMAL, 51: HARD,             # 1 2 3
    97: EASY, 98: NORMAL, 99: HARD,             # 1 2 3 на цифровом блоке
}

# Запасной путь: имена клавиш Tk, включая кириллические keysym.
BY_KEYSYM = {
    "Left": LEFT, "Right": RIGHT, "Down": DOWN, "Up": DROP,
    "a": LEFT, "d": RIGHT, "s": DOWN, "w": DROP,
    "A": LEFT, "D": RIGHT, "S": DOWN, "W": DROP,
    "space": DROP,
    "Escape": PAUSE, "p": PAUSE, "P": PAUSE,
    "r": RESTART, "R": RESTART,
    "Return": CONFIRM, "KP_Enter": CONFIRM,
    "1": EASY, "2": NORMAL, "3": HARD,
    "KP_1": EASY, "KP_2": NORMAL, "KP_3": HARD,
    # те же физические клавиши, но с русской раскладкой
    "Cyrillic_ef": LEFT, "Cyrillic_ve": RIGHT, "Cyrillic_yeru": DOWN,
    "Cyrillic_tse": DROP, "Cyrillic_ze": PAUSE, "Cyrillic_ka": RESTART,
}


def action_for(keycode, keysym):
    """Какое действие соответствует нажатию; None — клавиша не занята."""
    action = BY_KEYCODE.get(keycode)
    if action is not None:
        return action
    return BY_KEYSYM.get(keysym)