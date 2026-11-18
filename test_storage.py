"""Тесты для storage.py: профиль, таблица лидеров, смена имени."""

import unittest
import tempfile
import os
import storage


class TestStorage(unittest.TestCase):
    """Проверка работы с профилем и таблицей лидеров."""

    def setUp(self):
        # Создаём временный файл для тестов
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()

    def tearDown(self):
        # Удаляем временный файл
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_default_name(self):
        """Проверка имени по умолчанию."""
        self.assertEqual(storage.DEFAULT_NAME, "Игрок")
        self.assertEqual(storage.clean_name(""), storage.DEFAULT_NAME)
        self.assertEqual(storage.clean_name(None), storage.DEFAULT_NAME)

    def test_name_cleaning(self):
        """Проверка очистки имени."""
        self.assertEqual(storage.clean_name("  Вася  "), "Вася")
        self.assertEqual(storage.clean_name("   "), storage.DEFAULT_NAME)
        self.assertEqual(storage.clean_name("А" * 20), "А" * storage.MAX_NAME_LEN)

    def test_empty_profile(self):
        """Проверка пустого профиля."""
        profile = storage.empty()
        self.assertEqual(profile["version"], storage.SCHEMA_VERSION)
        self.assertEqual(profile["current"], storage.DEFAULT_NAME)
        self.assertEqual(profile["entries"], [])

    def test_load_empty_file(self):
        """Проверка загрузки из несуществующего файла."""
        profile = storage.load("nonexistent.json")
        self.assertEqual(profile["current"], storage.DEFAULT_NAME)
        self.assertEqual(profile["entries"], [])

    def test_save_and_load(self):
        """Проверка сохранения и загрузки."""
        profile = storage.empty()
        profile["current"] = "Тестовый игрок"
        profile["entries"] = [
            {"name": "Игрок1", "score": 1000},
            {"name": "Игрок2", "score": 500}
        ]
        
        storage.save(self.temp_file.name, profile)
        loaded = storage.load(self.temp_file.name)
        
        self.assertEqual(loaded["current"], "Тестовый игрок")
        self.assertEqual(len(loaded["entries"]), 2)
        self.assertEqual(loaded["entries"][0]["score"], 1000)
        self.assertEqual(loaded["entries"][1]["score"], 500)

    def test_set_current(self):
        """Проверка установки текущего имени."""
        profile = storage.empty()
        name = storage.set_current(profile, "Новый игрок")
        self.assertEqual(name, "Новый игрок")
        self.assertEqual(profile["current"], "Новый игрок")

    def test_add_score(self):
        """Проверка добавления очков в таблицу."""
        profile = storage.empty()
        
        # Добавляем первую запись
        result = storage.add_score(profile, "Игрок1", 1000)
        self.assertTrue(result)
        self.assertEqual(len(profile["entries"]), 1)
        self.assertEqual(profile["entries"][0]["score"], 1000)
        
        # Добавляем вторую запись
        result = storage.add_score(profile, "Игрок2", 500)
        self.assertTrue(result)
        self.assertEqual(len(profile["entries"]), 2)
        self.assertEqual(profile["entries"][0]["score"], 1000)
        
        # Добавляем запись с тем же именем
        result = storage.add_score(profile, "Игрок1", 1500)
        self.assertTrue(result)
        self.assertEqual(len(profile["entries"]), 3)
        # Проверяем сортировку
        self.assertEqual(profile["entries"][0]["score"], 1500)
        self.assertEqual(profile["entries"][1]["score"], 1000)

    def test_invalid_scores(self):
        """Проверка добавления некорректных очков."""
        profile = storage.empty()
        
        # Отрицательный счёт
        result = storage.add_score(profile, "Игрок1", -100)
        self.assertFalse(result)
        self.assertEqual(len(profile["entries"]), 0)
        
        # Ноль
        result = storage.add_score(profile, "Игрок1", 0)
        self.assertFalse(result)
        self.assertEqual(len(profile["entries"]), 0)
        
        # Булево значение
        result = storage.add_score(profile, "Игрок1", True)
        self.assertFalse(result)
        self.assertEqual(len(profile["entries"]), 0)

    def test_top_limit(self):
        """Проверка ограничения количества записей."""
        profile = storage.empty()
        
        # Добавляем больше 25 записей
        for i in range(30):
            storage.add_score(profile, f"Игрок{i}", 1000 - i * 10)
        
        # Проверяем, что осталось только 25
        self.assertEqual(len(profile["entries"]), storage.MAX_ENTRIES)
        
        # Проверяем, что остались лучшие результаты
        self.assertEqual(profile["entries"][0]["score"], 1000)
        self.assertEqual(profile["entries"][-1]["score"], 760)

    def test_best_score(self):
        """Проверка лучшего счёта игрока."""
        profile = storage.empty()
        storage.add_score(profile, "Игрок1", 1000)
        storage.add_score(profile, "Игрок2", 500)
        storage.add_score(profile, "Игрок1", 1500)
        
        self.assertEqual(storage.best(profile, "Игрок1"), 1500)
        self.assertEqual(storage.best(profile, "Игрок2"), 500)
        self.assertEqual(storage.best(profile, "Игрок3"), 0)

    def test_high_score(self):
        """Проверка лучшего счёта в таблице."""
        profile = storage.empty()
        storage.add_score(profile, "Игрок1", 1000)
        storage.add_score(profile, "Игрок2", 1500)
        storage.add_score(profile, "Игрок1", 500)
        
        self.assertEqual(storage.high_score(profile), 1500)

    def test_top_scores(self):
        """Проверка получения топ-счётов."""
        profile = storage.empty()
        storage.add_score(profile, "Игрок1", 1000)
        storage.add_score(profile, "Игрок2", 1500)
        storage.add_score(profile, "Игрок3", 500)
        
        top = storage.top(profile, 2)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0], ("Игрок2", 1500))
        self.assertEqual(top[1], ("Игрок1", 1000))

    def test_old_format_conversion(self):
        """Проверка преобразования старого формата."""
        # Создаём файл со старым форматом
        old_data = {
            "players": {
                "Игрок1": 1000,
                "Игрок2": 500
            }
        }
        
        with open(self.temp_file.name, 'w', encoding='utf-8') as f:
            import json
            json.dump(old_data, f)
        
        # Загружаем и проверяем преобразование
        profile = storage.load(self.temp_file.name)
        self.assertEqual(profile["current"], storage.DEFAULT_NAME)
        self.assertEqual(len(profile["entries"]), 2)
        self.assertEqual(profile["entries"][0]["score"], 1000)
        self.assertEqual(profile["entries"][1]["score"], 500)


if __name__ == "__main__":
    unittest.main()