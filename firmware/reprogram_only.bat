@echo off
REM ==========================================================================
REM  reprogram_only.bat -- isolated MCP4728 address reprogram build
REM
REM  Builds and flashes main_reprogram_only.cpp -- uses ONLY the legacy
REM  driver/i2c.h stack, does not include the new driver/i2c_master.h.
REM  Everything else (PCF8575, MCP4725, LCD, encoder, Si5351, bringup
REM  task) is excluded.  Prints SUCCESS or FAIL to serial.
REM
REM  Reflash bringup.bat after successful reprogram to return to normal.
REM
REM  Usage:
REM    reprogram_only.bat            (COM11 default)
REM    reprogram_only.bat COM7       (force a different port)
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

set "PORT=COM11"
if not "%~1"=="" set "PORT=%~1"

echo.
echo === MCP4728 reprogram (legacy i2c driver only) on %PORT% ===
echo (Ctrl+] to exit monitor when done)
echo.

REM ---- fullclean is REQUIRED here: switching to REPROGRAM_ONLY changes the
REM      SRCS list in CMakeLists.txt, and ninja doesn't always pick up SRCS
REM      changes without a fresh configure.
idf.py fullclean
idf.py -p %PORT% -DREPROGRAM_ONLY=ON build flash monitor

endlocal
