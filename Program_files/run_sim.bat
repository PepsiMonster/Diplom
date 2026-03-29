@echo off
setlocal

REM ============================================================================
REM build.bat
REM ============================================================================
REM Полный batch-скрипт для:
REM   1. запуска полного конвейера моделирования;
REM   2. упаковки исходников и результатов в ZIP;
REM   3. сохранения архива в папку artifacts.
REM
REM Требования:
REM   - Windows
REM   - установлен Python и доступен как "python" или "py -3"
REM   - PowerShell доступен для Compress-Archive
REM ============================================================================

cd /d "%~dp0"

echo ============================================================
echo Project root: %CD%
echo ============================================================

REM --------------------------------------------------------------------------
REM Определяем интерпретатор Python
REM --------------------------------------------------------------------------
set "PYTHON_CMD=python"

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python interpreter not found.
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=py -3"
    )
)

echo Using interpreter: %PYTHON_CMD%

REM --------------------------------------------------------------------------
REM Создаём timestamp через PowerShell
REM --------------------------------------------------------------------------
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"

set "ARTIFACTS_DIR=artifacts"
set "PACKAGE_DIR=%ARTIFACTS_DIR%\package_%STAMP%"
set "ZIP_PATH=%ARTIFACTS_DIR%\simulation_project_%STAMP%.zip"

if not exist "%ARTIFACTS_DIR%" mkdir "%ARTIFACTS_DIR%"
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

echo ============================================================
echo Running full pipeline...
echo ============================================================

%PYTHON_CMD% run.py full --suite-name full_pipeline --output-root results
if errorlevel 1 (
    echo [ERROR] Pipeline failed.
    pause
    exit /b 1
)

echo ============================================================
echo Collecting source files...
echo ============================================================

for %%F in (
    model.py
    params.py
    simulation.py
    experiments.py
    plots.py
    run.py
    build.bat
) do (
    if exist "%%F" copy /Y "%%F" "%PACKAGE_DIR%\" >nul
)

if exist "results" xcopy /E /I /Y "results" "%PACKAGE_DIR%\results" >nul

REM --------------------------------------------------------------------------
REM Удаляем явный мусор, если он появился
REM --------------------------------------------------------------------------
for /d /r "%PACKAGE_DIR%" %%D in (__pycache__ .pytest_cache .mypy_cache .ruff_cache) do (
    if exist "%%D" rmdir /s /q "%%D"
)

del /s /q "%PACKAGE_DIR%\*.pyc" >nul 2>nul
del /s /q "%PACKAGE_DIR%\*.pyo" >nul 2>nul

echo ============================================================
echo Creating ZIP archive...
echo ============================================================

if exist "%ZIP_PATH%" del /f /q "%ZIP_PATH%"

powershell -NoProfile -Command ^
    "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"

if errorlevel 1 (
    echo [ERROR] ZIP archive creation failed.
    pause
    exit /b 1
)

echo ============================================================
echo Done.
echo Archive: %ZIP_PATH%
echo Package dir: %PACKAGE_DIR%
echo ============================================================

pause
