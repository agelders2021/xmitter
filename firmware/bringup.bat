@echo off
REM ==========================================================================
REM  bringup.bat -- one-shot build + flash + monitor for the LCD bring-up test
REM
REM  Usage:
REM    bringup.bat            (auto-detect COM port)
REM    bringup.bat COM7       (force a specific COM port)
REM
REM  Runs from a plain cmd.exe -- activates the ESP-IDF environment itself,
REM  so you don't need the "ESP-IDF PowerShell" shortcut.  Exits the monitor
REM  with Ctrl+].
REM ==========================================================================

setlocal

REM ---- ESP-IDF install path (identical on primary + secondary machines,
REM      per Documentation notes; if EIM ever moves, edit this line).
set "IDF_EXPORT=D:\esp\v5.4.4\v5.4.4\esp-idf\export.bat"

if not exist "%IDF_EXPORT%" (
    echo.
    echo ERROR: ESP-IDF not found at:
    echo   %IDF_EXPORT%
    echo Update IDF_EXPORT at the top of bringup.bat, or reinstall via EIM.
    exit /b 1
)

call "%IDF_EXPORT%"
if errorlevel 1 (
    echo ESP-IDF export failed.
    exit /b 1
)

REM ---- cd into the firmware dir (where this .bat lives)
cd /d "%~dp0"

REM ---- Optional COM port arg
REM ---- Metro's USB CDC always enumerates as COM11 on this bench.  Override
REM      by passing another port name as the first arg.
set "PORT=COM11"
if not "%~1"=="" set "PORT=%~1"

echo.
echo === Building LCD_BRINGUP=ON, then flash + monitor on %PORT% ===
echo (Ctrl+] to exit monitor)
echo.

REM ---- fullclean is REQUIRED when returning from reprogram_only.bat --
REM      the SRCS list changed and ninja needs a fresh configure.  Cheap
REM      insurance in general.
idf.py fullclean
idf.py -p %PORT% -DLCD_BRINGUP=ON build flash monitor

endlocal
