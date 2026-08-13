@echo off
REM ==========================================================================
REM  ldac_scope.bat -- LDAC continuity diagnostic build
REM
REM  Builds and flashes a special firmware that skips normal boot and just
REM  toggles GPIO 7 (Arduino D7 / MCP4728 LDAC line) at 100 Hz forever.
REM  Put a scope probe on the MCP4728 breakout's LDAC pin: if you see a
REM  clean 100 Hz square wave between 0 V and 3.3 V, D7 -> LDAC is wired
REM  correctly.  If you see nothing (or a stuck DC level), the wire is
REM  broken / not soldered / going to the wrong pin.
REM
REM  Reflash with bringup.bat to go back to normal operation.
REM
REM  Usage:
REM    ldac_scope.bat            (auto-detect COM port)
REM    ldac_scope.bat COM7       (force a specific COM port)
REM ==========================================================================

setlocal

set "IDF_EXPORT=D:\esp\v5.4.4\v5.4.4\esp-idf\export.bat"

if not exist "%IDF_EXPORT%" (
    echo.
    echo ERROR: ESP-IDF not found at:
    echo   %IDF_EXPORT%
    exit /b 1
)

call "%IDF_EXPORT%"
if errorlevel 1 (
    echo ESP-IDF export failed.
    exit /b 1
)

cd /d "%~dp0"

set "PORT_ARG="
if not "%~1"=="" set "PORT_ARG=-p %~1"

echo.
echo === LDAC scope test (100 Hz on GPIO 7 / Arduino D7) ===
echo (Ctrl+] to exit monitor when done)
echo.

REM ---- fullclean first, so switching modes (bringup.bat <-> ldac_scope.bat)
REM      always produces a fresh binary.  ESP-IDF's build cache does not
REM      always pick up -D flag changes without a real code diff.
idf.py fullclean
idf.py %PORT_ARG% -DLCD_BRINGUP=ON -DLDAC_SCOPE_ONLY=ON build flash monitor

endlocal
