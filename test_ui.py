"""Тесты окна: одиночный шаг вбок и подсветка столбцов.

Тесты создают настоящее окно Tk и сразу прячут его. Если tkinter недоступен
(например, на сервере без графической среды), тесты помечаются пропущенными.
"""

import time
import unittest
from types import SimpleNamespace

import tkinter as tk

import game as g
import ui


class TkTestCase(unittest.TestCase):
    """Общая подготовка: спрятанное окно без игровых таймеров."""

    def setUp(self):
        try:
            self.app = ui.SnaketrisApp()
        except tk.TclError:
            self.skipTest("tkinter недоступен")
        self.app.root.withdraw()
        self.app._cancel_timer()
        self.app._stop_lateral()
        self.app.game = g.Game()
        self.app.redraw()

    def tearDown(self):
        app = getattr(self, "app", None)
        if app is None:
            return
        try:
            app._cancel_timer()
            app._stop_lateral()
            app.root.destroy()
        except tk.TclError:
            pass

    def press(self, keycode, keysym):
        self.app._on_key_press(SimpleNamespace(
            widget=self.app.root, keycode=keycode, keysym=keysym))

    def release(self, keycode, keysym):
        self.app._on_key_release(SimpleNamespace(
            widget=self.app.root, keycode=keycode, keysym=keysym))


class TestLateralTap(TkTestCase):
    """Одиночное нажатие должно давать ровно один шаг."""

    def test_single_press_moves_one_cell(self):
        x, y = self.app.game.snake.head
        self.press(39, "Right")                  # →
        self.assertEqual(self.app.game.snake.head, (x + 1, y))

    def test_tap_is_one_cell_even_with_fast_repeat(self):
        """Даже при повторе в 1 мс короткое нажатие не двигает дважды."""
        self.app.game.lateral_interval_ms = lambda soft_drop=False: 1
        x, y = self.app.game.snake.head
        self.press(39, "Right")
        time.sleep(0.06)                         # меньше паузы перед повтором
        self.app.root.update()
        self.release(39, "Right")
        self.app.root.update()
        self.assertEqual(self.app.game.snake.head, (x + 1, y))

    def test_hold_repeat_still_moves(self):
        """Автоповтор при удержании продолжает работать."""
        x, y = self.app.game.snake.head
        self.press(39, "Right")
        # Отменяем запланированный повтор и вызываем его вручную — так тест
        # не зависит от реального времени.
        if self.app.lateral_timer is not None:
            self.app.root.after_cancel(self.app.lateral_timer)
            self.app.lateral_timer = None
        self.app._repeat_lateral()
        self.assertEqual(self.app.game.snake.head, (x + 2, y))


class TestGuides(TkTestCase):
    """Подсветка столбцов под змейкой."""

    def test_guides_reach_bottom_of_field(self):
        self.app.game.snake = g.Snake([(3, 4), (4, 4), (4, 5)], 1)
        self.app.canvas.delete("all")
        self.app._draw_guides()

        items = self.app.canvas.find_withtag("guide")
        self.assertEqual(len(items), 2, "по одному прямоугольнику на столбец")
        tops = []
        for item in items:
            x1, y1, x2, y2 = self.app.canvas.coords(item)
            self.assertEqual(y2, ui.FIELD_H)
            tops.append(y1)
        # столбец 3 — от сегмента (3,4), столбец 4 — от нижнего (4,5)
        self.assertEqual(sorted(tops), [4 * ui.CELL, 5 * ui.CELL])


if __name__ == "__main__":
    unittest.main()
