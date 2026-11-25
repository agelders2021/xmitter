@echo off
REM ==========================================================================
REM  backpack.bat -- build + flash + monitor for the Rev A LCD bring-up with
REM                  a PCF8574 "I2C LCD" backpack (16x2) instead of the
REM                  WH2004A / PCF8575 front-panel driver.
REM
REM  Backpack auto-detected on 0x27 (PCF8574T) or 0x3F (PCF8574AT).
REM
REM  Usage:
REM    backpack.bat            (auto-detect COM port)
REM    backpack.bat COM12      (force a specific COM port)
REM ==========================================================================

setlocal

set "IDF_EXPORT=D:\esp\v5.4.4\v5.4.4\esp-idf\export.bat"

if not exist "%IDF_EXPORT%" (
    echo.
    echo ERROR: ESP-IDF not found at:
    echo   %IDF_EXPORT%
    echo Update IDF_EXPORT at the top of backpack.bat, or reinstall via EIM.
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
echo === Building LCD_BRINGUP=ON LCD_BACKPACK=ON, then flash + monitor ===
echo (Ctrl+] to exit monitor)
echo.

idf.py fullclean
idf.py %PORT_ARG% -DLCD_BRINGUP=ON -DLCD_BACKPACK=ON build flash monitor

endlocal
