"""Тесты для game.py: правила, константы, физика, сложности."""

import unittest
import game as g
from unittest.mock import MagicMock


class TestGame(unittest.TestCase):
    """Проверка правил игры."""

    def setUp(self):
        self.game = g.Game()

    def test_field_size(self):
        """Проверка размеров поля."""
        self.assertEqual(g.WIDTH, 10)
        self.assertEqual(g.HEIGHT, 20)

    def test_spawn_zone(self):
        """Проверка зоны появления."""
        self.assertEqual(g.SPAWN_ROWS, 4)
        self.assertEqual(g.SPAWN_COLUMNS, (4, 5))

    def test_difficulties(self):
        """Проверка пресетов сложности."""
        self.assertEqual(len(g.DIFFICULTIES), 3)
        self.assertIn("easy", g.DIFFICULTIES)
        self.assertIn("normal", g.DIFFICULTIES)
        self.assertIn("hard", g.DIFFICULTIES)

        easy = g.DIFFICULTIES["easy"]
        self.assertEqual(easy["title"], "Лёгкая")
        self.assertEqual(easy["base_ms"], 700)
        self.assertEqual(easy["min_ms"], 40)

        normal = g.DIFFICULTIES["normal"]
        self.assertEqual(normal["title"], "Обычная")
        self.assertEqual(normal["base_ms"], 600)
        self.assertEqual(normal["min_ms"], 25)

        hard = g.DIFFICULTIES["hard"]
        self.assertEqual(hard["title"], "Сложная")
        self.assertEqual(hard["base_ms"], 500)
        self.assertEqual(hard["min_ms"], 12)

    def test_snake_length(self):
        """Проверка длины змейки."""
        # При создании игра должна сразу спавнить змейку
        self.assertIsNotNone(self.game.snake)
        # Длина должна быть между 2 и 4
        self.assertIn(len(self.game.snake.cells), range(2, 5))

    def test_movement(self):
        """Проверка движения змейки."""
        # Сохраняем начальное положение
        initial_cells = self.game.snake.cells.copy()
        
        # Двигаем вниз
        result = self.game.tick()
        self.assertEqual(len(result), 0)  # Линий не должно быть очищено
        
        # Проверяем, что змейка сдвинулась
        self.assertNotEqual(self.game.snake.cells, initial_cells)
        
        # Проверяем, что голова действительно ниже
        initial_head_y = initial_cells[0][1]
        new_head_y = self.game.snake.head[1]
        self.assertEqual(new_head_y, initial_head_y + 1)

    def test_collision_with_wall(self):
        """Проверка коллизии со стенками."""
        # Пытаемся двигаться влево от левой стены
        self.game.snake = g.Snake([(0, 10)], 1)
        result = self.game._try_move(-1, 0)
        self.assertFalse(result)

    def test_line_clearing(self):
        """Проверка очистки линий."""
        # Заполняем нижнюю строку
        for x in range(g.WIDTH):
            self.game.board[19][x] = 1
        
        # Очищаем линии
        cleared = self.game.clear_lines()
        self.assertEqual(len(cleared), 1)
        self.assertEqual(cleared[0], 19)
        
        # Проверяем, что строка стала пустой
        self.assertEqual(self.game.board[19], [g.EMPTY] * g.WIDTH)

    def test_scoring(self):
        """Проверка подсчёта очков."""
        # Заполняем и очищаем линию
        for x in range(g.WIDTH):
            self.game.board[19][x] = 1
        
        # Очищаем линии и фиксируем змейку
        self.game.lock()
        
        # Проверяем, что очки начислены
        self.assertEqual(self.game.score, 100)  # SCORE_PER_LINE * level (1)
        
        # Проверяем уровень
        self.assertEqual(self.game.level, 1)

    def test_hard_drop(self):
        """Проверка мгновенного сброса."""
        # Проверяем, что hard_drop начисляет очки
        initial_score = self.game.score
        cleared = self.game.hard_drop()
        final_score = self.game.score
        
        # Очки должны увеличиться
        self.assertGreater(final_score, initial_score)
        # Проверяем, что змейка зафиксирована (lock() должен вернуть очищенные линии)
        self.assertEqual(cleared, [])  # в данном случае линии не очищаются

    def test_pause(self):
        """Проверка паузы."""
        # Ставим на паузу
        status = self.game.toggle_pause()
        self.assertEqual(status, g.PAUSED)
        
        # Снимаем с паузы
        status = self.game.toggle_pause()
        self.assertEqual(status, g.PLAYING)

    def test_game_over(self):
        """Проверка окончания игры."""
        # Блокируем зону спавна
        for x in g.SPAWN_COLUMNS:
            self.game.board[0][x] = 1
        
        # Пытаемся спавнить новую змейку
        result = self.game.spawn()
        self.assertFalse(result)
        self.assertEqual(self.game.status, g.GAME_OVER)

    def test_lateral_single_step(self):
        """Один вызов движения вбок сдвигает ровно на одну клетку."""
        self.game.snake = g.Snake([(4, 5), (4, 4)], 1)
        self.game.lateral_used = 0
        self.assertTrue(self.game.move_lateral(g.RIGHT))
        self.assertEqual(self.game.snake.head, (5, 5))

    def test_lateral_three_steps_per_tick(self):
        """За один такт разрешено ровно три шага вбок."""
        self.game.snake = g.Snake([(2, 5), (2, 4)], 1)
        self.game.lateral_used = 0
        for step in range(1, g.LATERAL_PER_TICK + 1):
            self.assertTrue(self.game.move_lateral(g.RIGHT))
            self.assertEqual(self.game.snake.head, (2 + step, 5))
        self.assertFalse(self.game.move_lateral(g.RIGHT))
        self.assertEqual(self.game.snake.head, (2 + g.LATERAL_PER_TICK, 5))

    def _locked_cells(self, color=1):
        return [(x, y) for y in range(g.HEIGHT) for x in range(g.WIDTH)
                if self.game.board[y][x] == color]

    @staticmethod
    def _normalized(cells):
        left = min(x for x, y in cells)
        top = min(y for x, y in cells)
        return sorted((x - left, y - top) for x, y in cells)

    def test_hard_drop_keeps_shape(self):
        """Сброс не меняет форму: все сегменты едут вниз на одном расстоянии."""
        self.game.board = [[g.EMPTY] * g.WIDTH for _ in range(g.HEIGHT)]
        shape = [(5, 5), (4, 5), (4, 6)]      # изогнутая змейка
        self.game.snake = g.Snake(list(shape), 1)
        before = self._normalized(shape)
        self.game.hard_drop()
        locked = self._locked_cells()
        self.assertEqual(len(locked), len(shape))
        self.assertEqual(self._normalized(locked), before)

    def test_hard_drop_stops_above_block(self):
        """Препятствие под одним сегментом останавливает всю фигуру."""
        self.game.board = [[g.EMPTY] * g.WIDTH for _ in range(g.HEIGHT)]
        self.game.board[10][5] = 3            # блок под головой
        shape = [(5, 5), (4, 5), (4, 6)]
        self.game.snake = g.Snake(list(shape), 1)
        self.game.hard_drop()
        locked = set(self._locked_cells())
        self.assertEqual(locked, {(5, 9), (4, 9), (4, 10)})
        self.assertNotIn((5, 10), locked)     # клетка занята блоком


if __name__ == "__main__":
    unittest.main()