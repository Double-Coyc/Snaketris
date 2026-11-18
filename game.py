"""Правила игры «Змейка-Тетрис».

Модуль намеренно ничего не знает про tkinter и про цвета: он хранит только
состояние поля и меняет его по правилам. Поэтому правила можно проверить
без окна — см. test_game.py.

Координаты: (x, y), x — столбец слева направо, y — ряд сверху вниз.
Левая верхняя клетка поля — (0, 0).
"""

from __future__ import annotations

import random

# ---------- параметры игры (все числа собраны здесь) ----------

WIDTH = 10                  # ширина поля в клетках
HEIGHT = 20                 # высота поля в клетках

SPAWN_COLUMNS = (4, 5)      # два центральных столбца — там появляется змейка
SPAWN_ROWS = 4              # сколько верхних рядов считается зоной появления

BASE_TICK_MS = 600          # такт на первом уровне: 0.6 с на одну клетку
SPEED_FACTOR = 0.7          # каждый уровень сокращает такт до 70% предыдущего
MIN_TICK_MS = 25            # предел: 20 клеток × 25 мс = 0.5 с на весь столбец
LINES_PER_LEVEL = 5         # столько линий нужно на новый уровень

SOFT_DROP_FACTOR = 10       # во сколько раз быстрее падение при зажатой ↓
MIN_SOFT_TICK_MS = 10       # но не чаще одного такта в 10 мс

DEFAULT_DIFFICULTY = "normal"

# Пресеты сложности: base_ms — такт на первом уровне, factor — доля такта,
# которая остаётся на следующем уровне, min_ms — предел скорости.
# min_ms × HEIGHT и есть время падения через всё поле:
#   лёгкая  — 40 × 20 = 0.8 с
#   обычная — 25 × 20 = 0.5 с
#   сложная — 12 × 20 = 0.24 с
DIFFICULTIES = {
    "easy": {"title": "Лёгкая", "base_ms": 700, "factor": 0.80, "min_ms": 40},
    "normal": {"title": "Обычная", "base_ms": BASE_TICK_MS,
               "factor": SPEED_FACTOR, "min_ms": MIN_TICK_MS},
    "hard": {"title": "Сложная", "base_ms": 500, "factor": 0.60, "min_ms": 12},
}

LATERAL_PER_TICK = 3        # сколько шагов вбок разрешено между падениями

# Горизонтальное движение при удержании ←/→: новый шаг не чаще, чем раз
# в max(MIN_LATERAL_MS, такт × LATERAL_FACTOR). Интервал привязан к текущей
# скорости, поэтому на быстрой игре змейка успевает доехать до края поля.
LATERAL_FACTOR = 0.4
MIN_LATERAL_MS = 15

SCORE_PER_LINE = 100        # база за линию, умножается на уровень и множитель
SCORE_SOFT_DROP = 1         # за клетку ускоренного падения (клавиша «вниз»)
SCORE_HARD_DROP = 2         # за клетку мгновенного сброса (пробел)

COLOR_COUNT = 5             # сколько цветов есть у змеек

EMPTY = 0                   # пустая клетка поля

PLAYING = "playing"
PAUSED = "paused"
GAME_OVER = "gameover"

DOWN = (0, 1)
LEFT = -1                   # шаг влево: dx для move_lateral
RIGHT = 1                   # шаг вправо: dx для move_lateral


class Snake:
    """Падающая змейка.

    cells — список пар (x, y) от головы к хвосту. Голова всегда cells[0],
    именно она задаёт движение. Сегменты тела идут за головой по её следу,
    поэтому змейка гнётся и может пролезть в щель шириной в одну клетку.
    """

    def __init__(self, cells, color):
        self.cells = cells
        self.color = color

    @property
    def head(self):
        return self.cells[0]


class Game:
    """Всё состояние одной партии и все правила в одном классе."""

    def __init__(self, rng=None, difficulty=DEFAULT_DIFFICULTY):
        # rng принимается снаружи, чтобы в тестах можно было задать seed
        self.rng = rng if rng is not None else random.Random()
        self.difficulty = difficulty if difficulty in DIFFICULTIES else DEFAULT_DIFFICULTY
        self.reset()

    # ---------- состояние ----------

    def reset(self):
        """Начать партию заново: поле пустое, счёт нулевой."""
        self.board = [[EMPTY] * WIDTH for _ in range(HEIGHT)]
        self.snake = None
        self.next_length = self._roll_length()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.tick_ms = DIFFICULTIES[self.difficulty]["base_ms"]
        self.status = PLAYING
        self.lateral_used = 0
        self.spawn_count = 0
        self.last_cleared = []      # какие ряды исчезли на последнем ходу
        self.spawn()

    def set_difficulty(self, name):
        """Сменить сложность и начать партию заново. False — неизвестное имя."""
        if name not in DIFFICULTIES:
            return False
        self.difficulty = name
        self.reset()
        return True

    def _roll_length(self):
        """Случайная длина следующей змейки: от 2 до 4 сегментов."""
        return self.rng.randint(2, 4)

    # ---------- поле ----------

    def cell_at(self, x, y):
        """Что находится в клетке: 0 — пусто, иначе номер цвета блока."""
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            return self.board[y][x]
        return None

    def _head_can_enter(self, x, y):
        """Может ли голова встать в клетку (x, y).

        Запрещены: выход за поле, вход в блок и вход в собственное тело.
        Хвост проверяется отдельно: он освобождает свою клетку в этом же
        ходу, поэтому в неё заходить можно.
        """
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            return False
        if self.board[y][x] != EMPTY:
            return False
        for bx, by in self.snake.cells[:-1]:     # без последнего сегмента
            if bx == x and by == y:
                return False
        return True

    # ---------- движение ----------

    def _try_move(self, dx, dy):
        """Сдвинуть голову на вектор. Тело тянется за ней.

        Возвращает True, если шаг удался. Если шаг невозможен, состояние
        не меняется вовсе — змейка не «ломается» и не теряет форму.
        """
        if self.snake is None:
            return False
        hx, hy = self.snake.head
        nx, ny = hx + dx, hy + dy
        if not self._head_can_enter(nx, ny):
            return False

        # «Следуй за лидером»: новый список = новая голова + все прежние
        # сегменты, кроме последнего (хвост сдвигается вперёд).
        self.snake.cells = [(nx, ny)] + self.snake.cells[:-1]
        return True

    def move_lateral(self, dx):
        """Шаг вбок по нажатию игрока. dx — это -1 (влево) или +1 (вправо)."""
        if self.status != PLAYING:
            return False
        if self.lateral_used >= LATERAL_PER_TICK:
            return False
        if not self._try_move(dx, 0):
            return False
        self.lateral_used += 1
        return True

    def tick(self, soft_drop=False):
        """Один такт игрового времени: падение на одну клетку вниз.

        Возвращает список исчезнувших рядов (пустой список, если змейка
        просто сместилась).
        """
        if self.status != PLAYING:
            return []

        # Лимит шагов вбок сбрасывается на каждом такте: игрок снова может
        # сдвинуть змейку три раза, пока она не упала на следующую клетку.
        self.lateral_used = 0

        if self._try_move(*DOWN):
            if soft_drop:
                self.score += SCORE_SOFT_DROP
            return []

        # Вниз хода нет — змейка упёрлась. Фиксируем её на поле.
        return self.lock()

    def drop_distance(self):
        """На сколько клеток вниз может уехать змейка, не меняя формы.

        Проверяем все сегменты сразу: фигура опускается целиком, поэтому
        препятствие под любым сегментом останавливает весь сброс.
        """
        if self.snake is None:
            return 0
        distance = 0
        while True:
            step = distance + 1
            if any(y + step >= HEIGHT or self.board[y + step][x] != EMPTY
                   for x, y in self.snake.cells):
                return distance
            distance = step

    def hard_drop(self):
        """Мгновенный сброс до упора (пробел) с начислением очков.

        Форма фиксируется в момент нажатия: все сегменты сдвигаются вниз
        на одно и то же расстояние, поэтому змейка приземляется такой же,
        какой была до сброса. Обычное падение по такту при этом сохраняет
        прежнее поведение — тело тянется за головой.
        """
        if self.status != PLAYING or self.snake is None:
            return []
        distance = self.drop_distance()
        if distance:
            self.snake.cells = [(x, y + distance) for x, y in self.snake.cells]
        self.score += distance * SCORE_HARD_DROP
        return self.lock()

    # ---------- фиксация и линии ----------

    def lock(self):
        """Превратить змейку в блоки поля и запустить следующую.

        Порядок важен: сначала блоки, потом очистка линий, потом проверка
        зоны появления. Иначе игра закончилась бы, хотя линия освободила
        место под новую змейку.
        """
        if self.snake is None:
            return []

        for x, y in self.snake.cells:
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                self.board[y][x] = self.snake.color

        self.snake = None
        cleared = self.clear_lines()
        self.last_cleared = cleared

        if cleared:
            # Множитель за мультилинию: 1 линия — x1, 2 — x2, 3 — x4, 4 — x8.
            multiplier = 2 ** (len(cleared) - 1)
            self.score += SCORE_PER_LINE * self.level * multiplier

        self.lines += len(cleared)
        self._update_level()
        self.spawn()
        return cleared

    def clear_lines(self):
        """Удалить полностью заполненные ряды, сдвинув всё верхнее вниз."""
        full_rows = [y for y in range(HEIGHT) if all(cell != EMPTY for cell in self.board[y])]
        for y in full_rows:
            del self.board[y]
            self.board.insert(0, [EMPTY] * WIDTH)
        return full_rows

    def _update_level(self):
        """Уровень и скорость зависят только от числа собранных линий.

        Скорость растёт пропорционально: каждый новый уровень — это 70%
        предыдущего такта, поэтому первые уровни меняются заметно, а к
        десятому такт упирается в MIN_TICK_MS и весь столбец змейка
        пролетает примерно за полсекунды.
        """
        self.level = 1 + self.lines // LINES_PER_LEVEL
        settings = DIFFICULTIES[self.difficulty]
        step = settings["factor"] ** (self.level - 1)
        self.tick_ms = max(settings["min_ms"], int(round(settings["base_ms"] * step)))

    def interval_ms(self, soft_drop=False):
        """Через сколько миллисекунд случится следующий такт.

        Правило тайминга живёт здесь, а не в ui.py: так его можно проверить
        тестами без окна.
        """
        if soft_drop:
            return max(MIN_SOFT_TICK_MS, self.tick_ms // SOFT_DROP_FACTOR)
        return self.tick_ms

    def lateral_interval_ms(self, soft_drop=False):
        """Пауза между шагами вбок, пока клавиша ←/→ зажата.

        Интервал пропорционален текущему такту: max(15 мс, такт × 0.4).
        На медленной игре шаги редкие, на быстрой — частые, поэтому змейка
        успевает сдвинуться до края поля, пока падает.
        """
        tick = self.interval_ms(soft_drop=soft_drop)
        return max(MIN_LATERAL_MS, int(round(tick * LATERAL_FACTOR)))

    def fall_time_ms(self):
        """Сколько идёт падение через всё поле на текущей скорости."""
        return self.tick_ms * HEIGHT

    # ---------- появление змейки ----------

    def spawn_zone_is_free(self):
        """Свободна ли зона появления: два центральных столбца, 4 верхних ряда."""
        for x in SPAWN_COLUMNS:
            for y in range(SPAWN_ROWS):
                if self.board[y][x] != EMPTY:
                    return False
        return True

    def spawn(self):
        """Поставить новую змейку сверху. False — если места нет (проигрыш)."""
        if not self.spawn_zone_is_free():
            self.status = GAME_OVER
            self.snake = None
            return False

        column = SPAWN_COLUMNS[self.rng.randint(0, len(SPAWN_COLUMNS) - 1)]
        length = self.next_length
        self.next_length = self._roll_length()

        self.spawn_count += 1
        color = 1 + (self.spawn_count - 1) % COLOR_COUNT

        # Голова в нижней клетке тела, тело уходит вверх: змейка висит
        # вертикально и падает вниз, а хвост остаётся выше головы. Если
        # поставить голову сверху, она упрётся в собственный второй сегмент
        # и змейка зафиксируется на первом же такте.
        self.snake = Snake([(column, y) for y in range(length - 1, -1, -1)], color)
        self.lateral_used = 0
        return True

    # ---------- пауза ----------

    def toggle_pause(self):
        """Поставить или снять игру с паузы (на экране Game Over не работает)."""
        if self.status == PLAYING:
            self.status = PAUSED
        elif self.status == PAUSED:
            self.status = PLAYING
        return self.status