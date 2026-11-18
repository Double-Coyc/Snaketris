@echo off
setlocal EnableDelayedExpansion

set "PATH_FILE=python_path.txt"
set "PYTHON_EXE="

rem 1. Читаем сохраненный путь
if exist "%PATH_FILE%" (
    set /p SAVED_PATH=<"%PATH_FILE%"
    if exist "!SAVED_PATH!" (
        set "PYTHON_EXE=!SAVED_PATH!"
    )
)

rem 2. Если не нашли, ищем сами
if not defined PYTHON_EXE (
    if exist "python.cmd" (
        for /f "delims=" %%i in ('call python.cmd -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE (
            for /f "delims=" %%j in ('"%%i" -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%j"
        )
    )
)

rem 3. Спрашиваем через окно (и сохраняем БЕЗ кавычек)
if not defined PYTHON_EXE (
    for /f "delims=" %%i in ('powershell -NoProfile -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.OpenFileDialog; $f.Filter = 'python.exe|python.exe'; $f.Title = [char]0x0423+[char]0x043A+[char]0x0430+[char]0x0436+[char]0x0438+[char]0x0442+[char]0x0435+[char]0x0020+[char]0x043F+[char]0x0443+[char]0x0442+[char]0x044C+[char]0x0020+[char]0x043A+[char]0x0020+[char]0x0444+[char]0x0430+[char]0x0439+[char]0x043B+[char]0x0443+[char]0x0020+[char]0x0070+[char]0x0079+[char]0x0074+[char]0x0068+[char]0x006F+[char]0x006E+[char]0x002E+[char]0x0065+[char]0x0078+[char]0x0065; if ($f.ShowDialog() -eq 'OK') { $f.FileName }"') do set "PYTHON_EXE=%%i"
    
    if defined PYTHON_EXE (
        set "CLEAN_PATH=!PYTHON_EXE:"=!"
        >"%PATH_FILE%" echo !CLEAN_PATH!
    )
)

if not defined PYTHON_EXE (
    pause
    exit /b
)

"!PYTHON_EXE!" main.py
if errorlevel 1 pause
