# ESP-IDF Setup on Windows

Concise install reference for the xmitter firmware toolchain.
Target: ESP-IDF v5.4.4 LTS, Adafruit Metro ESP32-S3.

Total time: ~1 hour, mostly waiting on the ~2 GB EIM download.

## Prerequisites

| Item | Notes |
|---|---|
| Windows 10/11, current updates | Run Windows Update first if machine has been idle |
| Git for Windows | https://git-scm.com/download/win — defaults are fine |
| Python 3.11 or 3.12 | 3.12.x confirmed working with v5.4.4. Do NOT install 3.13 (untested) |
| ~5 GB free disk on install drive | ESP-IDF source + toolchain |
| xmitter repo cloned | `git clone https://github.com/agelders2021/xmitter.git` |

## Step 1: VS Code

Download User Installer from https://code.visualstudio.com/download. Custom
destination is fine (e.g. `D:\Programs\Microsoft VS Code`). Keep "Add to PATH"
checked. Install all four context-menu / file-association options.

## Step 2: ESP-IDF Extension

In VS Code: **Ctrl+Shift+X**, search `ESP-IDF`, install the one by
**Espressif Systems** (top result).

## Step 3: Open the xmitter workspace

**File → Open Folder** → cloned xmitter directory. "Yes, I trust the authors".

## Step 4: Launch EIM (Installation Manager)

Click the red Espressif icon in the left activity bar → expand the **Advanced**
section in the COMMANDS list → **Open ESP-IDF Installation Manager**.

When the "EIM executable not found, choose a mirror" popup appears, pick
**github.com**. If antivirus (e.g. Malwarebytes) flags a Tsinghua probe,
block it — that mirror is unsafe to use from the US and EIM will auto-skip it.

## Step 5: EIM Custom Install

Pick **Custom Installation** (Easy doesn't expose mirror or version choices).

| EIM step | Choice |
|---|---|
| Target Chips | Uncheck "All", check only `esp32s3` |
| IDF Version | **`v5.4.4`** (Stable Releases / LTS line — not v6.0.x) |
| Mirrors | Leave defaults: github.com / dl.espressif.com / pypi.org |
| Features | `core` only — skip gdbgui, pytest, ci, docs, ide |
| Tools | Required only (12 pre-checked). Skip optional `qemu-xtensa` |
| Installation Path | `D:\esp\v5.4.4` (or `C:\esp\v5.4.4` if no D:) — short, no spaces |

Wait for the ~2 GB download. Resumes if interrupted.

## Step 6: Reconnect VS Code to the install

Close EIM. In VS Code, three notifications appear in the bottom-right:

1. **"No standard ESP-IDF project was found... Activate Anyway?"** → click
   **Activate Anyway**. (xmitter root has no CMakeLists.txt — that's expected.)
2. **"Extension configuration is not valid"** → dismiss with X.
3. **"Error initializing OpenOCD error monitor"** → dismiss with **Cancel**
   (NOT Report). Clears after step below.

If the right-hand Chat panel is hiding notifications, click the bell icon in
the bottom-right status bar to view them all.

In the ESP-IDF sidebar (COMMANDS list):

- Click **Select current ESP-IDF version** (2nd item) → pick the v5.4.4 entry.

Status bar should change from `ESP-IDF vx.x` to **`ESP-IDF v5.4.4`**.

**Skip** "Set Espressif Device Target" — it errors with no project, that's
fine. Target gets set per-project once `firmware/` is scaffolded.

## Step 7: Verify

Sidebar → **Open ESP-IDF Terminal**. In the terminal:

```
idf.py --version
```

Should print `ESP-IDF v5.4.4`. Toolchain is verified, install is complete.

## Paths created on disk

| Path | What |
|---|---|
| `D:\esp\v5.4.4\v5.4.4\esp-idf` | ESP-IDF source (EIM nests version dir twice) |
| `C:\Espressif\tools` | Toolchain binaries (EIM puts on C: regardless of install root) |
| `%USERPROFILE%\.espressif\eim_gui` | EIM itself |
| `.vscode/settings.json` in workspace | Machine-specific extension config — **gitignored** |

## Gotchas

- **"Configure ESP-IDF Extension"** command no longer exists in extension
  v2.1.0+. Use the Installation Manager flow above instead.
- **Activate Anyway** notification can hide behind the Chat panel. Close the
  panel or use the bell icon in the status bar to find it.
- **EIM defaults to a Chinese mirror** on first launch. Custom Install
  exposes the mirror selection screen so you can override.
- **The extension does NOT auto-link to the EIM install.** You must run
  `Select current ESP-IDF version` to wire them up.
- **`idf.py set-target` requires a CMakeLists.txt at the workspace root.**
  Don't bother running it until a firmware project exists.

## Hardware-side step (for the machine where the Metro lives)

After Steps 1-7 work and a firmware project exists:

- Plug in Metro ESP32-S3 via USB-C
- Check Device Manager → Ports — should show as "USB Serial Device (COMxx)"
- If "Unknown USB Device", install Silicon Labs CP210x VCP driver from
  https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- Build, flash, monitor via VS Code (**Ctrl+E B / F / M**) or `idf.py build flash monitor`

## Keep both machines in sync

- Pin both to the same IDF version (v5.4.4 here)
- Keep `.vscode/` gitignored — each machine writes its own paths
- Enable VS Code Settings Sync (gear icon → Backup and Sync Settings) to
  share theme, extensions, keybindings via your Microsoft/GitHub account
