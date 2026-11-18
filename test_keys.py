"""Тесты для keys.py: таблица клавиш."""

import unittest
import keys


class TestKeys(unittest.TestCase):
    """Проверка таблицы управления."""

    def test_basic_actions(self):
        """Проверка основных действий."""
        # Проверяем коды клавиш
        self.assertEqual(keys.BY_KEYCODE[37], keys.LEFT)    # стрелка влево
        self.assertEqual(keys.BY_KEYCODE[39], keys.RIGHT)   # стрелка вправо
        self.assertEqual(keys.BY_KEYCODE[40], keys.DOWN)    # стрелка вниз
        self.assertEqual(keys.BY_KEYCODE[38], keys.DROP)    # стрелка вверх
        self.assertEqual(keys.BY_KEYCODE[32], keys.DROP)   # пробел
        self.assertEqual(keys.BY_KEYCODE[27], keys.PAUSE)  # Esc
        self.assertEqual(keys.BY_KEYCODE[80], keys.PAUSE)  # P
        self.assertEqual(keys.BY_KEYCODE[82], keys.RESTART) # R
        self.assertEqual(keys.BY_KEYCODE[13], keys.CONFIRM) # Enter

    def test_wasd_alternatives(self):
        """Проверка альтернативных клавиш WASD."""
        self.assertEqual(keys.BY_KEYCODE[65], keys.LEFT)    # A
        self.assertEqual(keys.BY_KEYCODE[68], keys.RIGHT)   # D
        self.assertEqual(keys.BY_KEYCODE[83], keys.DOWN)    # S
        self.assertEqual(keys.BY_KEYCODE[87], keys.DROP)    # W

    def test_difficulty_keys(self):
        """Проверка клавиш сложности."""
        self.assertEqual(keys.BY_KEYCODE[49], keys.EASY)   # 1
        self.assertEqual(keys.BY_KEYCODE[50], keys.NORMAL) # 2
        self.assertEqual(keys.BY_KEYCODE[51], keys.HARD)   # 3
        self.assertEqual(keys.BY_KEYCODE[97], keys.EASY)  # 1 на цифровом блоке
        self.assertEqual(keys.BY_KEYCODE[98], keys.NORMAL) # 2 на цифровом блоке
        self.assertEqual(keys.BY_KEYCODE[99], keys.HARD)  # 3 на цифровом блоке

    def test_keysym_mapping(self):
        """Проверка mapping по keysym."""
        self.assertEqual(keys.BY_KEYSYM["Left"], keys.LEFT)
        self.assertEqual(keys.BY_KEYSYM["Right"], keys.RIGHT)
        self.assertEqual(keys.BY_KEYSYM["Down"], keys.DOWN)
        self.assertEqual(keys.BY_KEYSYM["Up"], keys.DROP)
        self.assertEqual(keys.BY_KEYSYM["a"], keys.LEFT)
        self.assertEqual(keys.BY_KEYSYM["d"], keys.RIGHT)
        self.assertEqual(keys.BY_KEYSYM["s"], keys.DOWN)
        self.assertEqual(keys.BY_KEYSYM["w"], keys.DROP)
        self.assertEqual(keys.BY_KEYSYM["space"], keys.DROP)
        self.assertEqual(keys.BY_KEYSYM["Escape"], keys.PAUSE)
        self.assertEqual(keys.BY_KEYSYM["p"], keys.PAUSE)
        self.assertEqual(keys.BY_KEYSYM["P"], keys.PAUSE)
        self.assertEqual(keys.BY_KEYSYM["r"], keys.RESTART)
        self.assertEqual(keys.BY_KEYSYM["R"], keys.RESTART)
        self.assertEqual(keys.BY_KEYSYM["Return"], keys.CONFIRM)
        self.assertEqual(keys.BY_KEYSYM["KP_Enter"], keys.CONFIRM)

    def test_russian_layout(self):
        """Проверка русской раскладки."""
        self.assertEqual(keys.BY_KEYSYM["Cyrillic_ef"], keys.LEFT)    # ф
        self.assertEqual(keys.BY_KEYSYM["Cyrillic_ve"], keys.RIGHT)   # в
        self.assertEqual(keys.BY_KEYSYM["Cyrillic_yeru"], keys.DOWN)  # ы
        self.assertEqual(keys.BY_KEYSYM["Cyrillic_tse"], keys.DROP)   # ц
        self.assertEqual(keys.BY_KEYSYM["Cyrillic_ze"], keys.PAUSE)   # з
        self.assertEqual(keys.BY_KEYSYM["Cyrillic_ka"], keys.RESTART) # к

    def test_action_for(self):
        """Проверка функции определения действия."""
        # По keycode
        self.assertEqual(keys.action_for(37, "Left"), keys.LEFT)
        self.assertEqual(keys.action_for(65, "a"), keys.LEFT)
        
        # По keysym
        self.assertEqual(keys.action_for(999, "Left"), keys.LEFT)  # несуществующий keycode
        self.assertEqual(keys.action_for(999, "Cyrillic_ef"), keys.LEFT)
        
        # Неизвестная клавиша
        self.assertIsNone(keys.action_for(999, "Unknown"))

    def test_difficulty_actions(self):
        """Проверка действий сложности."""
        self.assertEqual(keys.DIFFICULTY_ACTIONS, (keys.EASY, keys.NORMAL, keys.HARD))


if __name__ == "__main__":
    unittest.main()