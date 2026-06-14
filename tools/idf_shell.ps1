# =============================================================================
#  tools/idf_shell.ps1 — one-shot ESP-IDF environment loader for the xmitter
#  firmware. Skips the VS Code ESP-IDF extension entirely (which trips over
#  the repo's lack of a CMakeLists.txt at the root) and just gets a working
#  PowerShell ready to run idf.py inside firmware/.
#
#  USAGE (PowerShell):
#
#    # Interactive — dot-source so the env stays in YOUR shell:
#    . .\tools\idf_shell.ps1
#    idf.py build
#    idf.py flash monitor
#
#    # One-shot — pass args directly (no need to dot-source):
#    .\tools\idf_shell.ps1 flash monitor
#    .\tools\idf_shell.ps1 build
#    .\tools\idf_shell.ps1 -p COM7 flash monitor
#
#  Note the leading `. ` on the interactive form — without it the env
#  changes disappear when the script ends.
#
#  Both machines (primary dev + secondary hardware-interface) have the
#  same EIM install layout (see Documentation/ESP-IDF_Setup_Windows.md), so
#  the hard-coded paths below match on either machine.  Update IDF_VERSION
#  if you ever move off v5.4.4.
# =============================================================================

$IDF_VERSION = 'v5.4.4'
$IDF_PROFILE = "C:\Espressif\tools\Microsoft.$IDF_VERSION.PowerShell_profile.ps1"

if (-not (Test-Path $IDF_PROFILE)) {
    Write-Error "ESP-IDF profile not found at $IDF_PROFILE. Has EIM finished installing $IDF_VERSION?"
    return
}

# Load the EIM-generated profile: sets IDF_PATH, activates the Python venv,
# puts idf.py / esptool.py on PATH, defines an `idf.py` alias.  Quiet the
# banner — we'll print our own one-liner instead.
. $IDF_PROFILE *> $null

# Force IDF_TARGET=esp32s3 regardless of what the VS Code extension may have
# stashed in the parent environment.  This is the single biggest source of
# `set-target` mysteriously bailing out.
$env:IDF_TARGET = 'esp32s3'

# Drop into firmware/ — that's where the IDF project lives.  $PSScriptRoot is
# the directory this script sits in (tools/), so .. is the repo root.
$FW_DIR = Join-Path $PSScriptRoot '..\firmware'
if (-not (Test-Path $FW_DIR)) {
    Write-Error "firmware/ directory not found at $FW_DIR"
    return
}
Set-Location $FW_DIR

Write-Host ''
Write-Host "ESP-IDF $IDF_VERSION env loaded, target=$env:IDF_TARGET, cwd=$(Get-Location)" -ForegroundColor Green
Write-Host "  Common commands:" -ForegroundColor DarkGray
Write-Host "    idf.py set-target esp32s3       # first time on a fresh machine" -ForegroundColor DarkGray
Write-Host "    idf.py build" -ForegroundColor DarkGray
Write-Host "    idf.py flash monitor            # build + flash + serial console (Ctrl+] to exit monitor)" -ForegroundColor DarkGray
Write-Host "    idf.py -p COM<n> flash monitor  # if auto-detect picks the wrong port" -ForegroundColor DarkGray
Write-Host ''

# If args were passed, run them through idf.py and exit.  Otherwise leave
# the user sitting in the shell.
if ($args.Count -gt 0) {
    & idf.py @args
}
