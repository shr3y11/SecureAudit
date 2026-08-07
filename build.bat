@echo off
setlocal

cd /d "%~dp0"

echo.
echo ========================================
echo SecureAudit Windows Build
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] SecureAudit virtual environment was not found.
    echo Create or restore .venv before building.
    exit /b 1
)

if not exist "SecureAudit.spec" (
    echo [ERROR] SecureAudit.spec was not found.
    exit /b 1
)

echo [1/2] Running PyInstaller...
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm SecureAudit.spec

if errorlevel 1 (
    echo.
    echo [ERROR] SecureAudit build failed.
    exit /b 1
)

echo.
echo [2/2] Build completed successfully.
echo Output:
echo %CD%\dist\SecureAudit.exe
echo.

endlocal
