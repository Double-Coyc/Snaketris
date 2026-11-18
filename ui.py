"""Окно Snaketris: отрисовка на Canvas, панель и обработка клавиш.

Вся игровая логика лежит в game.py. Этот модуль — только «кожа»: он
показывает состояние игры и переводит нажатия клавиш в вызовы методов Game.
Такое разделение позволяет менять оформление, не трогая правила.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import app_info
import game as g
import keys
import storage

# ---------- внешний вид ----------

CELL = 32                       # размер клетки в пикселях
FIELD_W = g.WIDTH * CELL        # 320
FIELD_H = g.HEIGHT * CELL       # 640
PAD = 16                        # отступ окна
PANEL_W = 260                   # ширина панели справа (увеличена для лидеров)

BG = "#0e1524"                  # фон окна
PANEL_BG = "#131c2e"            # фон панели
FIELD_BG = "#0b1120"            # фон поля
GRID = "#182238"                # линии сетки
TEXT = "#e6edf8"
MUTED = "#8492ad"
ACCENT = "#6cc7ff"
BUTTON_BG = "#1d2a40"
BUTTON_ACTIVE = "#27395a"

# Цвета змеек: яркие — для падающей, приглушённые — для уже лежащих блоков.
SNAKE_COLORS = ["#4fc3f7", "#ffb74d", "#ce93d8", "#4db6ac", "#ef9a9a"]
BLOCK_COLORS = ["#2a5f7a", "#7a5a2f", "#5f4569", "#2f5f5c", "#7a4a4a"]

BEST_FILE = Path(__file__).with_name("best_score.txt")
LEADERBOARD_FILE = Path(__file__).with_name("leaderboard.json")
LEADERS_SHOWN = storage.TOP_LIMIT

# Пауза перед первым автоповтором движения вбок. Одиночное нажатие успевает
# отпуститься раньше, поэтому сдвигает ровно на одну клетку даже на сложной
# сложности, где повтор идёт каждые 15 мс.
LATERAL_REPEAT_DELAY_MS = 180


class SnaketrisApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(app_info.TITLE + " — тетрис со змейками")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        
        # Расположение поля и панели
        self.field = tk.Canvas(self.root, width=FIELD_W, height=FIELD_H,
                               bg=FIELD_BG, highlightthickness=0)
        self.field.pack(side="left", padx=PAD, pady=PAD)
        
        # Состояние
        self.profile = storage.load(str(LEADERBOARD_FILE))
        self.player_name = storage.set_current(self.profile, "")
        self.game = g.Game(difficulty=self._get_difficulty())
        self.soft_drop = False
        self.result_saved = False
        
        panel = tk.Frame(self.root, bg=PANEL_BG, width=PANEL_W)
        panel.pack(side="right", fill="y", padx=(0, PAD), pady=PAD)
        panel.pack_propagate(False)
        self._build_panel(panel)
        
        # Создаем псевдоним для field как canvas для совместимости
        self.canvas = self.field
        
        # Таймеры и клавиши
        self.timer = None
        self.lateral_timer = None
        self.lateral_dir = 0
        self.first_run = True
        
        # Связываем клавиши
        self._bind_keys()
        
        # Первое отображение и запуск
        self.redraw()
        self._start_timer()
        
        # Фокус на поле, чтобы клавиши работали сразу
        self.root.after(50, self.root.focus_force)

    def _get_difficulty(self):
        """Прочитать пресет сложности из сохранённого профиля или вернуть normal."""
        # В версии 0.1.0 сложности ещё не сохранялись, всегда normal
        return "normal"

    def _build_panel(self, panel):
        # Название и версия — в одном месте, см. app_info.py.
        header = tk.Frame(panel, bg=PANEL_BG)
        header.pack(fill="x")
        tk.Label(header, text=app_info.NAME.upper(), bg=PANEL_BG, fg=ACCENT,
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(header, text="v" + app_info.VERSION, bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right", pady=(4, 0))

        tk.Label(panel, text="СЧЁТ", bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.score_label = tk.Label(panel, text="0", bg=PANEL_BG, fg=TEXT,
                                    font=("Segoe UI", 26, "bold"))
        self.score_label.pack(anchor="w", pady=(0, 2))

        self.rows = {}
        for key, title in (("lines", "Линии"), ("level", "Уровень"),
                           ("difficulty", "Сложность"),
                           ("next", "Следующая"), ("best", "Рекорд")):
            row = tk.Frame(panel, bg=PANEL_BG)
            row.pack(fill="x")
            tk.Label(row, text=title, bg=PANEL_BG, fg=MUTED,
                     font=("Segoe UI", 9)).pack(side="left")
            value = tk.Label(row, text="—", bg=PANEL_BG, fg=TEXT,
                             font=("Segoe UI", 10, "bold"))
            value.pack(side="right")
            self.rows[key] = value

        self._separator(panel)

        tk.Label(panel, text="ИГРОК", bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.name_entry = tk.Entry(panel, bg=FIELD_BG, fg=ACCENT,
                                   insertbackground=TEXT, relief="flat",
                                   font=("Segoe UI", 11, "bold"), width=16)
        self.name_entry.pack(fill="x", ipady=3, pady=(2, 4))
        self.name_entry.insert(0, self.player_name)
        self.name_entry.bind("<Return>", self._save_name)
        self.name_entry.bind("<KP_Enter>", self._save_name)
        self.name_entry.bind("<Escape>", self._reset_name_field)
        self.name_entry.bind("<FocusIn>", self._on_name_focus)
        self.name_entry.bind("<FocusOut>", self._on_name_blur)

        self._button(panel, "Сохранить имя", self._save_name).pack(fill="x")

        self._separator(panel)

        tk.Label(panel, text="ЛИДЕРЫ", bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        
        # Фрейм с прокруткой для таблицы лидеров
        leaderboard_frame = tk.Frame(panel, bg=PANEL_BG)
        leaderboard_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(leaderboard_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.leader_canvas = tk.Canvas(leaderboard_frame, bg=PANEL_BG, 
                                      highlightthickness=0, yscrollcommand=scrollbar.set)
        self.leader_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.leader_canvas.yview)
        
        self.leader_rows = []
        self.leader_frame = tk.Frame(self.leader_canvas, bg=PANEL_BG)
        self.leader_canvas.create_window((0, 0), window=self.leader_frame, anchor="nw")
        
        # Создаем 25 строк для таблицы лидеров
        for index in range(25):
            row = tk.Frame(self.leader_frame, bg=PANEL_BG)
            row.pack(fill="x")
            tk.Label(row, text=f"{index + 1}.", width=3, anchor="w",
                     bg=PANEL_BG, fg=MUTED,
                     font=("Segoe UI", 8)).pack(side="left")
            score = tk.Label(row, text="", anchor="e", bg=PANEL_BG, fg=TEXT,
                             font=("Segoe UI", 8, "bold"))
            score.pack(side="right")
            name = tk.Label(row, text="—", anchor="w", bg=PANEL_BG, fg=MUTED,
                            font=("Segoe UI", 8))
            name.pack(side="left", fill="x", expand=True)
            self.leader_rows.append((name, score))
        
        # Настройка прокрутки
        self.leader_frame.update_idletasks()
        self.leader_canvas.config(scrollregion=self.leader_canvas.bbox("all"))

        self._separator(panel)

        tk.Label(panel, text="УПРАВЛЕНИЕ", bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        controls = (
            "← →  A D   движение\n"
            "↓  S       ускорить падение\n"
            "Пробел  W  сбросить вниз\n"
            "P/Esc  R   пауза, заново\n"
            "1 2 3      сложность"
        )
        tk.Label(panel, text=controls, bg=PANEL_BG, fg=TEXT, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w")

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=BUTTON_BG,
                         fg=TEXT, activebackground=BUTTON_ACTIVE,
                         activeforeground=TEXT, relief="flat", bd=0,
                         font=("Segoe UI", 9), pady=3, cursor="hand2")

    def _separator(self, panel):
        tk.Frame(panel, bg="#243149", height=1).pack(fill="x", pady=5)

    # ---------- имя игрока ----------

    def _focus_name_entry(self):
        self.first_run = False
        self.name_entry.focus_set()
        self.name_entry.select_range(0, "end")

    def _on_name_focus(self, event=None):
        # Пока человек печатает, змейка не должна ехать вбок по удержанию.
        self._stop_lateral()
        if self.first_run:
            self.root.after(100, self._focus_name_entry)

    def _on_name_blur(self, event=None):
        # При потере фокуса сохраняем имя, если оно изменилось
        current = self.name_entry.get()
        if current != self.player_name:
            self._save_name()

    def _reset_name_field(self, event=None):
        """Вернуть имя из профиля, если отменили ввод."""
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, self.player_name)

    def _save_name(self, event=None):
        """Сохранить введённое имя в профиль."""
        new_name = self.name_entry.get()
        if new_name != self.player_name:
            self.player_name = storage.set_current(self.profile, new_name)
            self._save_profile()
            self._update_leaders()

    def _save_profile(self):
        """Записать профиль на диск."""
        storage.save(str(LEADERBOARD_FILE), self.profile)

    # ---------- клавиши ----------

    def _bind_keys(self):
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.canvas.bind("<Button-1>", lambda event: self.root.focus_set())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self.root.focus_force)

    def _on_key_press(self, event):
        # Пока фокус в поле имени, клавиши принадлежат полю, а не игре.
        if event.widget is self.name_entry:
            return None

        # Действие определяется по коду клавиши, а не по символу: так WASD
        # и R работают и на русской раскладке. Таблица — в keys.py.
        action = keys.action_for(event.keycode, event.keysym)

        if action in (keys.LEFT, keys.RIGHT):
            dx = -1 if action == keys.LEFT else 1
            self._start_lateral(dx)
            return "break"

        if action == keys.DOWN:
            # Удерживание ↓ или S ускоряет падение и даёт очки за клетку.
            if not self.soft_drop:
                self.soft_drop = True
                if self.game.status == g.PLAYING:
                    self._start_timer()
            return "break"

        if action == keys.DROP:
            if self.game.status == g.PLAYING:
                self.game.hard_drop()
                self._sync()
            return "break"

        if action == keys.PAUSE:
            self.game.toggle_pause()
            self._sync()
            return "break"

        if action in keys.DIFFICULTY_ACTIONS:
            # Смена сложности начинает партию заново с новыми настройками.
            self.game.set_difficulty(action)
            self._sync()
            return "break"

        if action == keys.RESTART or (action == keys.CONFIRM
                                      and self.game.status == g.GAME_OVER):
            self._restart()
            return "break"

        return "break"

    def _on_key_release(self, event):
        if event.widget is self.name_entry:
            return None

        action = keys.action_for(event.keycode, event.keysym)
        if action in (keys.LEFT, keys.RIGHT):
            dx = -1 if action == keys.LEFT else 1
            if self.lateral_dir == dx:
                self._stop_lateral()
        if action == keys.DOWN and self.soft_drop:
            self.soft_drop = False
            if self.game.status == g.PLAYING:
                self._start_timer()
        return "break"

    # ---------- движение вбок при удержании ----------

    def _start_lateral(self, dx):
        """Первый шаг вбок и запуск плавного повторения."""
        if self.game.status != g.PLAYING:
            return
        if self.lateral_dir == dx:
            return      # это автоповтор Windows — движение уже идёт
        self._stop_lateral()
        self.lateral_dir = dx
        if self.game.move_lateral(dx):
            self.redraw()
            self._schedule_lateral(first=True)
        else:
            self.lateral_dir = 0

    def _schedule_lateral(self, first=False):
        """Запланировать следующий шаг вбок.

        Для первого повтора добавляем паузу ``LATERAL_REPEAT_DELAY_MS``:
        иначе на высокой скорости таймер успевал сработать ещё до того,
        как игрок отпустит клавишу, и одно нажатие сдвигало змейку дважды.
        Дальше повторы идут с прежним интервалом, пропорциональным падению.
        """
        if self.lateral_dir and self.game.status == g.PLAYING:
            delay = self.game.lateral_interval_ms(soft_drop=self.soft_drop)
            if first:
                delay = max(delay, LATERAL_REPEAT_DELAY_MS)
            self.lateral_timer = self.root.after(delay, self._repeat_lateral)

    def _repeat_lateral(self):
        self.lateral_timer = None
        if not self.lateral_dir or self.game.status != g.PLAYING:
            self.lateral_dir = 0
            return
        if not self.game.move_lateral(self.lateral_dir):
            self.lateral_dir = 0     # упёрлись в стену или в блок
            return
        self.redraw()
        self._schedule_lateral()

    def _stop_lateral(self):
        if self.lateral_timer is not None:
            self.root.after_cancel(self.lateral_timer)
            self.lateral_timer = None
        self.lateral_dir = 0

    # ---------- таймер ----------

    def _interval(self):
        """Сколько ждать до следующего падения (правило тайминга — в Game)."""
        return self.game.interval_ms(soft_drop=self.soft_drop)

    def _start_timer(self):
        self._cancel_timer()
        if self.game.status == g.PLAYING:
            self.timer = self.root.after(self._interval(), self._loop)

    def _cancel_timer(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None

    def _loop(self):
        """Один такт: сдвинуть игру и запланировать следующий."""
        self.timer = None
        if self.game.status != g.PLAYING:
            return
        self.game.tick(soft_drop=self.soft_drop)
        self._sync()

    def _sync(self):
        """После любого хода: сохранить результат, перерисовать, пустить таймер."""
        self._save_result()
        self.redraw()
        self._start_timer()

    def _restart(self):
        self._stop_lateral()
        self.game.reset()
        self.soft_drop = False
        self.result_saved = False
        self._sync()

    # ---------- таблица лидеров ----------

    def _save_result(self):
        """Когда партия закончилась — добавить её в таблицу лидеров."""
        if self.game.status != g.GAME_OVER or self.result_saved:
            return
        self.result_saved = True
        self._stop_lateral()
        if not storage.add_score(self.profile, self.player_name,
                                 self.game.score):
            return
        self._save_profile()
        self._update_leaders()

    # ---------- отрисовка ----------

    def redraw(self):
        self.canvas.delete("all")
        self._draw_grid()
        self._draw_spawn_zone()
        self._draw_guides()
        self._draw_blocks()
        self._draw_snake()
        self._draw_overlay()
        self._update_panel()

    def _draw_grid(self):
        for x in range(g.WIDTH + 1):
            self.canvas.create_line(x * CELL, 0, x * CELL, FIELD_H, fill=GRID)
        for y in range(g.HEIGHT + 1):
            self.canvas.create_line(0, y * CELL, FIELD_W, y * CELL, fill=GRID)

    def _draw_spawn_zone(self):
        """Пунктир вокруг зоны появления: два центральных столбца, 4 ряда.

        Без него кажется, что змейка «прыгает» на клетку влево: появляется
        она то в столбце 4, то в 5, а какая из клеток считается зоной
        поражения — не видно.
        """
        left = g.SPAWN_COLUMNS[0] * CELL
        right = (g.SPAWN_COLUMNS[-1] + 1) * CELL
        bottom = g.SPAWN_ROWS * CELL
        self.canvas.create_rectangle(left + 2, 2, right - 2, bottom - 2,
                                     outline="#2a3d5c", dash=(3, 5))

    def _draw_guides(self):
        """Подсветить столбцы змейки от её сегментов до низа поля.

        В каждом столбце берём самый нижний сегмент: всё, что выше, занято
        самой змейкой, а подсветка показывает, куда она может упасть.
        Рисуется до блоков, чтобы лежащие блоки перекрывали подсветку.
        """
        snake = self.game.snake
        if snake is None or self.game.status != g.PLAYING:
            return
        lowest = {}
        for x, y in snake.cells:
            lowest[x] = max(lowest.get(x, y), y)
        for x, y in lowest.items():
            self.canvas.create_rectangle(
                x * CELL + 1, y * CELL, x * CELL + CELL - 1, FIELD_H,
                fill=ACCENT, outline="", stipple="gray25", tags="guide")

    def _draw_blocks(self):
        for y in range(g.HEIGHT):
            for x in range(g.WIDTH):
                color = self.game.board[y][x]
                if color != g.EMPTY:
                    self._draw_block(x, y, BLOCK_COLORS[(color - 1) % len(BLOCK_COLORS)])

    def _draw_snake(self):
        snake = self.game.snake
        if snake is None:
            return
        color = SNAKE_COLORS[(snake.color - 1) % len(SNAKE_COLORS)]
        for x, y in snake.cells:
            self._draw_block(x, y, color)
        # Глаза на голове — чтобы было видно, куда змейка ползёт.
        hx, hy = snake.head
        for dx in (0.28, 0.62):
            x1 = hx * CELL + dx * CELL
            y1 = hy * CELL + 0.32 * CELL
            self.canvas.create_rectangle(x1, y1, x1 + 5, y1 + 5,
                                         fill=FIELD_BG, outline="")

    def _draw_block(self, x, y, color):
        x1 = x * CELL + 1
        y1 = y * CELL + 1
        self.canvas.create_rectangle(x1, y1, x1 + CELL - 2, y1 + CELL - 2,
                                     fill=color, outline=FIELD_BG, width=1)

    def _draw_overlay(self):
        if self.game.status == g.PLAYING:
            return

        self.canvas.create_rectangle(0, 0, FIELD_W, FIELD_H, fill=FIELD_BG, outline="")

        if self.game.status == g.PAUSED:
            self._center_text("ПАУЗА", 20, -18)
            self._center_text("P — продолжить", 11, 16, MUTED)
        else:
            self._center_text("ИГРА ОКОНЧЕНА", 18, -46)
            self._center_text(f"Счёт: {self.game.score}", 13, -8)
            self._center_text(f"Линии: {self.game.lines}", 12, 16, MUTED)
            self._center_text("R — начать заново", 11, 46, ACCENT)

    def _center_text(self, text, size, offset_y, color=TEXT):
        self.canvas.create_text(
            FIELD_W / 2,
            FIELD_H / 2 + offset_y,
            text=text,
            fill=color,
            font=("Segoe UI", size, "bold"),
        )

    def _update_panel(self):
        self.score_label.config(text=str(self.game.score))
        self.rows["lines"].config(text=str(self.game.lines))
        self.rows["level"].config(text=str(self.game.level))
        self.rows["difficulty"].config(
            text=g.DIFFICULTIES[self.game.difficulty]["title"])
        self.rows["next"].config(text=str(self.game.next_length))

        # «Рекорд» — лучший результат за всё время с учётом текущей партии.
        best = max(storage.high_score(self.profile), self.game.score)
        self.rows["best"].config(text=str(best))
        self._update_leaders()

    def _update_leaders(self):
        entries = storage.top(self.profile, 25)  # Показываем топ-25
        for index, (name_label, score_label) in enumerate(self.leader_rows):
            if index < len(entries):
                name, score = entries[index]
                current = name == self.player_name
                name_label.config(text=name, fg=ACCENT if current else TEXT)
                score_label.config(text=str(score),
                                   fg=ACCENT if current else TEXT)
            else:
                name_label.config(text="—", fg=MUTED)
                score_label.config(text="")

    # ---------- запуск ----------

    def _on_close(self):
        self._stop_lateral()
        self._cancel_timer()
        self.root.destroy()

    def run(self):
        self.root.mainloop()