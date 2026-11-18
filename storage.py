"""Локальный профиль и таблица лидеров Snaketris.

Данные лежат рядом с программой в обычном JSON-файле ``leaderboard.json``:

.. code-block:: json

    {
      "version": 2,
      "current": "Вася",
      "entries": [
        {"name": "Вася", "score": 1200},
        {"name": "Аня", "score": 900}
      ]
    }

``current`` — чьё имя подставлено в поле игрока, ``entries`` — лучшие
результаты игроков (по одной записи на уникальное имя). Список отсортирован
по убыванию счёта и обрезан до ``MAX_ENTRIES`` (25) записей.

Модуль не импортирует tkinter, поэтому его можно проверить тестами без
открытия окна — см. test_storage.py.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_NAME = "Игрок"      # имя, если поле оставили пустым
MAX_NAME_LEN = 14           # длиннее имя не поместится в панель
MAX_ENTRIES = 25            # сколько записей хранит таблица лидеров
TOP_LIMIT = 25              # сколько строк показывать в панели
SCHEMA_VERSION = 2          # версия формата файла


def clean_name(raw):
    """Привести введённое имя к аккуратному виду.

    Пустое имя заменяется на ``DEFAULT_NAME``, лишние пробелы убираются,
    слишком длинное имя обрезается.
    """
    text = " ".join(str(raw or "").split())
    return text[:MAX_NAME_LEN] if text else DEFAULT_NAME


def _entry(name, score):
    """Одна запись таблицы: имя и счёт."""
    return {"name": clean_name(name), "score": int(score)}


def _valid_score(value):
    """Счёт — целое неотрицательное число (bool не считается числом)."""
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _sorted(entries):
    """Оставить по одному лучшему результату на имя и отсортировать по убыванию."""
    best_by_name = {}
    for entry in entries:
        name = clean_name(entry["name"])
        score = int(entry["score"])
        if name not in best_by_name or score > best_by_name[name]["score"]:
            best_by_name[name] = {"name": name, "score": score}
    return sorted(best_by_name.values(), key=lambda entry: -entry["score"])[:MAX_ENTRIES]


def empty():
    """Пустой профиль: имя по умолчанию и ни одной записи."""
    return {"version": SCHEMA_VERSION, "current": DEFAULT_NAME, "entries": []}


def _entries_from_list(raw):
    """Разобрать новый формат: список словарей или пар ``[имя, счёт]``."""
    entries = []
    if not isinstance(raw, list):
        return entries
    for item in raw:
        name, score = None, None
        if isinstance(item, dict):
            name, score = item.get("name"), item.get("score")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            name, score = item
        if not _valid_score(score):
            continue
        entries.append(_entry(name, score))
    return entries


def _entries_from_players(raw):
    """Старый формат ``{"players": {имя: рекорд}}`` > список записей."""
    entries = []
    if isinstance(raw, dict):
        for name, score in raw.items():
            if _valid_score(score):
                entries.append(_entry(name, score))
    return entries


def load(path):
    """Прочитать профиль.

    Отсутствующий или испорченный файл — это не ошибка: просто начинаем
    с пустого профиля, и игра остаётся рабочей. Файл старого формата
    (``players``) читается и превращается в список записей.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty()
    if not isinstance(data, dict):
        return empty()

    profile = empty()
    profile["current"] = clean_name(data.get("current"))

    if "entries" in data:
        entries = _entries_from_list(data.get("entries"))
    else:
        entries = _entries_from_players(data.get("players"))

    profile["entries"] = _sorted(entries)
    return profile


def save(path, profile):
    """Записать профиль на диск.

    Сначала пишем во временный файл и только потом заменяем старый: если
    запись прервётся, таблица лидеров не останется наполовину записанной.
    """
    path = Path(path)
    text = json.dumps(profile, ensure_ascii=False, indent=2)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)


def set_current(profile, raw_name):
    """Запомнить, под каким именем играет человек.

    Возвращает очищенное имя.
    """
    name = clean_name(raw_name)
    profile["current"] = name
    return name


def add_score(profile, name, score):
    """Добавить или обновить лучший результат игрока в таблице.

    Если имя уже есть в лидерборде, счёт перезаписывается только тогда, когда
    новый результат строго больше предыдущего. Возвращает True, если таблица
    была обновлена.
    """
    if not _valid_score(score) or score <= 0:
        return False

    cleaned = clean_name(name)
    new_score = int(score)

    for entry in profile["entries"]:
        if entry["name"] == cleaned:
            if new_score > entry["score"]:
                entry["score"] = new_score
                profile["entries"] = _sorted(profile["entries"])
                return True
            return False

    profile["entries"].append({"name": cleaned, "score": new_score})
    profile["entries"] = _sorted(profile["entries"])
    return True


def best(profile, name):
    """Лучший счёт игрока; 0, если его нет в таблице."""
    cleaned = clean_name(name)
    for entry in profile["entries"]:
        if entry["name"] == cleaned:
            return entry["score"]
    return 0


def high_score(profile):
    """Лучший результат за всё время; 0, если таблица пуста."""
    return profile["entries"][0]["score"] if profile["entries"] else 0


def top(profile, limit=TOP_LIMIT):
    """Лучшие результаты: список ``(имя, счёт)`` по убыванию счёта."""
    return [(entry["name"], entry["score"]) for entry in profile["entries"][:limit]]
