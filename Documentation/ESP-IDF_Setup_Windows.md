# ESP-IDF Setup on a Fresh Windows Machine

End-to-end walkthrough for setting up the xmitter firmware development
environment from scratch. Target: Adafruit Metro ESP32-S3, C++ firmware
using native FreeRTOS, Python tooling for host-side calibration/build.

Plan: install everything needed in dependency order, verify each step
works before moving on. Total time: ~1-2 hours, mostly downloads.

---

## Pre-flight (do once at the start)

### 1. Windows Update

Machine has been sitting -- run Windows Update FIRST. Reboot when prompted.
This avoids weird permission/driver issues later when installing the toolchain.

```
Settings -> Windows Update -> Check for updates -> install everything
```

Don't skip this. Half of "ESP-IDF won't install" Stack Overflow questions are
fixed by Windows updating its USB drivers and runtime libraries.

### 2. Free disk space

ESP-IDF + tooling needs about **5 GB** on C:. Check `Settings -> Storage`
and clear out junk if needed before starting.

### 3. Install order

You'll install these in order. Each one is verified before the next:

1. Git for Windows
2. Python 3.11
3. Visual Studio Code
4. (Optional) Claude Code -- so you have it on this machine too
5. ESP-IDF Extension for VS Code (this handles the toolchain)
6. Test with the blink example

---

## Step 1: Git for Windows

**Why first**: you'll clone the xmitter repo to get this very file plus the
existing code, and ESP-IDF's setup uses git internally.

### Install

1. Go to https://git-scm.com/download/win
2. Download the 64-bit installer
3. Run it. **Accept all defaults** -- the defaults are sane.
   - Note: at the "Choosing the default editor" step you can pick VS Code if
     you want, but Vim default is fine.

### Verify

Open a fresh PowerShell or Command Prompt window:

```powershell
git --version
```

Should print something like `git version 2.45.x`. If not, close and reopen
the terminal -- PATH changes don't apply to already-open shells.

### Configure your identity

```powershell
git config --global user.name "Al Gelders"
git config --global user.email "agelders@lightspeed.net"
```

Match this to your existing GitHub identity from the xmitter project.

### Clone the xmitter repo

Pick a parent directory for the project. I'd suggest `C:\Users\AlAnd\dev\`
to keep it separate from your "Git Backed Projects" directory on the OTHER
machine.

```powershell
mkdir C:\Users\AlAnd\dev
cd C:\Users\AlAnd\dev
git clone https://github.com/agelders2021/xmitter.git
cd xmitter
```

You should now have the project including this very file at:
`C:\Users\AlAnd\dev\xmitter\Documentation\ESP-IDF_Setup_Windows.md`

---

## Step 2: Python 3.11

**Why**: ESP-IDF's build tools (`idf.py`) ARE Python. Calibration scripts and
host-side tooling for the xmitter project (the various `tools/*.py` files)
also need Python.

### Install

1. Go to https://www.python.org/downloads/windows/
2. Download **Python 3.11.x** (NOT 3.12 or 3.13 -- ESP-IDF v5.4 is verified
   on 3.11, newer versions may have rough edges)
3. Run the installer. **TWO IMPORTANT CHECKBOXES on the first screen:**
   - [x] **Add python.exe to PATH** -- absolutely required
   - [x] Use admin privileges when installing py.exe -- recommended
4. Click "Install Now" (uses defaults that are fine for our purposes)

### Verify

Open a fresh PowerShell window:

```powershell
python --version
```

Should print `Python 3.11.x`. If it says `Python was not found...` then PATH
didn't get updated -- re-run the installer with "Add to PATH" checked, OR
manually add `C:\Users\AlAnd\AppData\Local\Programs\Python\Python311\` and
`...\Python311\Scripts\` to PATH via System Properties.

### Install the project's Python packages

```powershell
cd C:\Users\AlAnd\dev\xmitter
pip install openpyxl reportlab matplotlib numpy
```

These are needed by the existing tooling (parts list, schematic PDFs, sweep
scripts). About 200 MB download, takes ~3 minutes.

---

## Step 3: Visual Studio Code

**Why**: this is the editor, terminal host, AND the launcher for ESP-IDF.

### Install

1. Go to https://code.visualstudio.com/download
2. Download the User Installer for Windows 64-bit
3. Run the installer. **Recommended checkboxes:**
   - [x] Create a desktop icon
   - [x] Add "Open with Code" action to Windows Explorer file context menu
   - [x] Add "Open with Code" action to Windows Explorer directory context menu
   - [x] Register Code as editor for supported file types
   - [x] Add to PATH (default)

### Verify

Open a fresh PowerShell:

```powershell
code --version
```

Should print three lines (version, commit hash, architecture). If `code` isn't
recognized, restart PowerShell.

### Open the xmitter project

```powershell
cd C:\Users\AlAnd\dev\xmitter
code .
```

That opens VS Code with the entire xmitter project as the workspace.
Familiarize yourself with the layout. The first time you open it, VS Code may
suggest a few extensions -- accept Python and C/C++ if it offers them.

---

## Step 4 (optional): Claude Code on this machine

If you want Claude available on this machine too:

```powershell
# Install via npm (requires Node.js first)
# 1. Install Node.js LTS from https://nodejs.org/
# 2. Then:
npm install -g @anthropic-ai/claude-code

# Verify:
claude --version

# Launch in the xmitter directory:
cd C:\Users\AlAnd\dev\xmitter
claude
```

First time: it'll prompt for OAuth login. Same account you use on the other
machine. (Skip this step if you're keeping Claude on just the one machine.)

---

## Step 5: ESP-IDF Extension for VS Code

This is the meat of the setup. The extension handles the toolchain, Python
venv, OpenOCD, and idf.py wrapper for you.

### Install the extension

1. Open VS Code
2. Click the Extensions icon in the left sidebar (or Ctrl+Shift+X)
3. Search for **"ESP-IDF"**
4. Install the one published by **"Espressif Systems"** (official). Should
   have ~1M+ installs and a fairly recent update date.

### Configure the extension

After install, the extension auto-opens its setup wizard. If not:

1. **Ctrl+Shift+P** (command palette)
2. Type: `ESP-IDF: Configure ESP-IDF Extension`
3. Press Enter

You'll see three options:

- **Express** -- Recommended for first install. Downloads everything.
- **Advanced** -- For when you already have IDF installed somewhere.
- **Use existing setup** -- N/A here.

**Pick Express.**

### Express install wizard

1. **ESP-IDF version**: pick **v5.4** (the current LTS as of this writing).
   If v5.5 has been released and is marked stable, use that.
2. **ESP-IDF Container Directory**: leave default (`C:\Users\AlAnd\esp`).
3. **ESP-IDF Tools Directory**: leave default (`C:\Users\AlAnd\.espressif`).
4. **Python**: it should auto-detect the Python 3.11 you installed in Step 2.
   If not, browse to `C:\Users\AlAnd\AppData\Local\Programs\Python\Python311\python.exe`.
5. Click **Install**.

Now wait. The extension downloads:
- ESP-IDF source (~1 GB git clone)
- xtensa-esp32s3-elf-gcc toolchain (~250 MB)
- OpenOCD-esp32 (~50 MB)
- Python venv for IDF tooling (~300 MB after pip installs)

**Total download: ~2 GB. Time: 10-30 minutes** depending on connection.

If it fails partway through, run it again -- it resumes.

When done, you'll see "ESP-IDF Configured Successfully" with a green check.

---

## Step 6: Verify with the blink example

### Create the blink project

1. **Ctrl+Shift+P** -> `ESP-IDF: Show Examples Projects`
2. The extension opens a sidebar showing categories. Navigate to
   **get-started/blink**.
3. Click "Create project using example blink"
4. Choose a parent directory: `C:\Users\AlAnd\dev\`
5. Project will be created at `C:\Users\AlAnd\dev\blink\`

### Set the target chip

In the bottom status bar of VS Code, look for the target chip. It probably
says `esp32` (default). Click it -> select **`esp32s3`**.

The extension may ask you to pick a flash method (UART, JTAG, DFU). For the
Metro ESP32-S3, choose **UART** -- it has a USB-to-serial converter onboard.

### Plug in the Metro ESP32-S3

USB-C cable to the Metro board's USB port. The board may show up as a single
USB CDC device on Windows. Check Device Manager -> Ports (COM & LPT) -- you
should see a "USB Serial Device (COMxx)" or similar.

If Windows can't identify the device, you may need the CP210x VCP driver
(Silicon Labs) -- download from
https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers . Install
and reboot. Then check Device Manager again.

### Build

In VS Code with the blink project open:

- **Ctrl+E B** -- starts the build. First build takes 2-3 minutes (CMake
  config + compile).
- Watch the terminal at the bottom for `Project build complete.`

### Flash

- **Ctrl+E F** -- starts the flash. Pick the COM port if asked.
- You'll see progress dots scrolling. Takes ~10-15 seconds.

### Monitor

- **Ctrl+E M** -- opens a serial monitor showing the boot log + your
  application output.
- The Metro's onboard LED should blink at ~1 Hz.

If the LED blinks, your environment is fully set up.

To exit the monitor, press **Ctrl+]** (right square bracket).

---

## Step 7: Set up the xmitter firmware skeleton

We'll do this together once you've got the environment running.

Quick sketch of what's coming:

```
xmitter/
  firmware/                    <- NEW directory
    main/
      CMakeLists.txt
      idf_component.yml
      keyer_envelope.cpp        (Adafruit-style envelope generator)
      keyer_envelope.h
      keyer_winkey.cpp          (WinKey emulation)
      keyer_winkey.h
      grid_bias_dac.cpp         (MCP4725 bias control)
      cathode_monitor.cpp       (ADS1115 / built-in ADC sampling)
      fault_handler.cpp         (CT_FAULT response, watchdog gate)
      main.cpp                  (RTOS task setup, pinning to core 1)
    CMakeLists.txt              (top-level)
    sdkconfig.defaults          (FreeRTOS tick = 1000 Hz, ...)
```

We'll write these together once the environment works. Topics we already
spec'd in `Documentation/cw_envelope_keyer.md`:

- Envelope LUT (raised cosine, 256 samples, predistorted)
- 25 µs tick via `esp_timer_get_time()` busy-wait
- Task pinned to core 1 via `xTaskCreatePinnedToCore`
- Dedicated SPI bus for the MCP4921 DAC
- Watchdog registration via `esp_task_wdt`

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `code` not recognized in PowerShell | Reopen PowerShell. VS Code installer adds to PATH but already-open shells don't see it. |
| Extension install hangs at "Downloading ESP-IDF" | Cancel, retry. Sometimes the git clone times out on slow connections. The extension resumes from where it left off. |
| `idf.py: command not found` in terminal | Use VS Code's built-in terminal -- the extension auto-activates the IDF environment in it. Or run `C:\Users\AlAnd\esp\v5.4\esp-idf\export.ps1` manually. |
| Metro shows as "Unknown USB Device" | Install Silicon Labs CP210x driver (link above). Reboot. |
| Build fails with "No CMake found" | Reinstall the extension. The Express setup is supposed to install CMake but occasionally misses it. Alt: install CMake separately from https://cmake.org/download/ . |
| Build fails with Python errors | The extension uses its own Python venv at `C:\Users\AlAnd\.espressif\python_env\idf5.4_py3.11_env\`. If your system Python changed, rerun `ESP-IDF: Configure ESP-IDF Extension`. |
| Flash fails with "Permission denied" on COM port | Another program (PuTTY, Arduino IDE, etc.) is holding the port. Close it. Or restart VS Code. |

---

## When you're stuck

Open Claude Code in this directory once it's running:

```powershell
cd C:\Users\AlAnd\dev\xmitter
claude
```

Then ask -- you've got the full project context including this setup doc,
the firmware design specs (`cw_envelope_keyer.md`, `pa_cathode_monitor.md`),
and all the hardware-side schematics.
