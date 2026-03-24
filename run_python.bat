@echo off
setlocal

REM ------------------------------------------------------------
REM run_program_test.bat
REM
REM Назначение:
REM 1) запустить MVP-версию симулятора из папки program_files_test
REM 2) после успешного запуска собрать ZIP-архив всей папки
REM    program_files_test в корне проекта
REM
REM Важно:
REM - .bat специально использует просто "python", а не абсолютный путь
REM   вроде C:\python314\python.exe
REM - это нужно для корректной работы с активированным conda-окружением
REM ------------------------------------------------------------

REM Корень проекта = папка, где лежит сам .bat
set "ROOT=%~dp0"

REM Путь к MVP-папке
set "PROJECT_DIR=%ROOT%program_files_test"

REM Имя итогового архива
set "ZIP_NAME=program_files_test.zip"
set "ZIP_PATH=%ROOT%%ZIP_NAME%"

echo.
echo ============================================
echo   RUN + ZIP for program_files_test
echo ============================================
echo.

REM ------------------------------------------------------------
REM Базовая проверка: существует ли run.py
REM ------------------------------------------------------------
if not exist "%PROJECT_DIR%\run.py" (
    echo [ERROR] Не найден файл:
    echo         "%PROJECT_DIR%\run.py"
    exit /b 1
)

REM ------------------------------------------------------------
REM Показываем, какой именно Python будет использован.
REM Это полезно после всех проблем с conda / python314.
REM ------------------------------------------------------------
echo [INFO] Используемый интерпретатор Python:
python -c "import sys; print(sys.executable)"
if errorlevel 1 (
    echo [ERROR] Команда python недоступна.
    echo         Сначала активируй окружение и проверь, что python виден в PATH.
    exit /b 1
)

echo.
echo [1/3] Переход в папку program_files_test...
pushd "%PROJECT_DIR%" || (
    echo [ERROR] Не удалось перейти в:
    echo         "%PROJECT_DIR%"
    exit /b 1
)

echo [2/3] Запуск run.py...
python run.py
if errorlevel 1 (
    echo [ERROR] Выполнение run.py завершилось с ошибкой.
    popd
    exit /b 1
)

REM Возвращаемся в корень проекта
popd

echo.
echo [3/3] Создание ZIP-архива...

REM Если архив уже существует, удаляем его, чтобы не было конфликта
if exist "%ZIP_PATH%" del /f /q "%ZIP_PATH%"

REM ------------------------------------------------------------
REM Упаковка всей папки program_files_test в ZIP.
REM Используем PowerShell Compress-Archive, т.к. он штатно есть в Windows.
REM ------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Compress-Archive -Path '%PROJECT_DIR%' -DestinationPath '%ZIP_PATH%' -Force"

if errorlevel 1 (
    echo [ERROR] Не удалось создать ZIP-архив:
    echo         "%ZIP_PATH%"
    exit /b 1
)

echo.
echo [OK] Запуск завершен успешно.
echo [OK] Архив создан:
echo      "%ZIP_PATH%"
echo.

endlocal
exit /b 0