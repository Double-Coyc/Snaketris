"""Точка входа в игру Snaketris.

Запуск:
    python.cmd main.py

Проверка без показа окна (используется при отладке):
    python.cmd main.py --smoke
"""

import sys

import app_info


def smoke():
    """Быстрая проверка: окно создаётся, игра крутится, ничего не падает."""
    from ui import SnaketrisApp

    app = SnaketrisApp()
    app.root.withdraw()          # окно не показываем
    app._cancel_timer()
    app._stop_lateral()

    for _ in range(80):
        app.game.tick()
        app.game.move_lateral(-1)
        app.game.move_lateral(1)
        app.redraw()

    app.game.toggle_pause()
    app.redraw()
    app.game.toggle_pause()

    app.game.hard_drop()
    app._sync()
    app.root.update()
    app.root.destroy()
    print(app_info.NAME + " " + app_info.VERSION + ": smoke ok")


def main():
    if "--smoke" in sys.argv:
        smoke()
        return

    from ui import SnaketrisApp

    SnaketrisApp().run()


if __name__ == "__main__":
    main()