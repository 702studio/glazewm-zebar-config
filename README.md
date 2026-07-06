# Windows Tiling WM & Bar Customization Setup (GlazeWM + Zebar)

This repository contains my personal, custom-tailored configuration environment for [GlazeWM](https://github.com/glzr-io/glazewm) (tiling window manager) and [Zebar](https://github.com/glzr-io/zebar) (customizable desktop status bar) on Windows. 

It includes a custom, background autotiling engine (`glaze_autotile.py`) to replicate AwesomeWM-style dynamic layouts (fair, columns, rows) through GlazeWM's local websocket IPC interface.

Designed to be **100% Agent-Friendly**: All paths, dependencies, hotkeys, and setup procedures are documented explicitly for AI coding agents and human administrators alike.

---

## 📂 Repository Directory Layout

```
.
├── bin/
│   ├── change_scale.ps1          # Powershell script to toggle display scaling
│   └── SetDpi.exe                # C++ binary helper to query/set Windows scaling DPI
├── glazewm/
│   └── config.yaml               # GlazeWM main configuration (hotkeys, workspace, gaps, window rules)
├── zebar/
│   ├── settings.json             # Zebar main settings (configures active starter pack on startup)
│   └── packs/
│       └── glzr-io.starter/      # Custom Zebar widgets and bar design
│           ├── styles.css        # Customized CSS stylesheet for the status bar
│           ├── with-glazewm.html # Webview HTML rendering widgets linked with GlazeWM
│           └── zpack.json        # Widget pack configuration metadata
├── glaze_autotile.py             # Python autotiling websocket engine (AwesomeWM fair layouts)
├── glaze-restart.bat             # Batch script to safely restart GlazeWM process
├── .gitignore                    # Local state and log file exclusions
└── README.md                     # This comprehensive setup guide
```

---

## 🎹 Comprehensive Hotkey Mapping (Keybindings)

GlazeWM controls are triggered using `Alt` as the modifier key. The keybindings are organized into functional groups below:

### 1. Workspace Focus & Navigation
| Shortcut | Action / Command | Description |
| :--- | :--- | :--- |
| `Alt + 1` to `9` | `focus --workspace 1-9` | Focus workspace number 1 through 9. |
| `Alt + J` | `focus --prev-workspace` | Focus the previous workspace in order. |
| `Alt + K` | `focus --next-workspace` | Focus the next workspace in order. |
| `Alt + A` | `focus --prev-active-workspace` | Focus the previous active workspace. |
| `Alt + S` | `focus --next-active-workspace` | Focus the next active workspace. |
| `Alt + D` | `focus --recent-workspace` | Focus the workspace that last had focus. |
| `Alt + Up / Down` | `focus --direction up / down` | Move window focus vertically. |

### 2. Window Movement & Workspace Relocation
| Shortcut | Action / Command | Description |
| :--- | :--- | :--- |
| `Alt + Shift + Up` | `move --direction up` | Swap focused window upwards. |
| `Alt + Shift + Down` | `move --direction down` | Swap focused window downwards. |
| `Alt + Shift + Left` | `move --direction left` | Swap focused window to the left. |
| `Alt + Shift + Right` | `move --direction right` | Swap focused window to the right. |
| `Alt + Shift + 1` to `9` | `move --workspace 1-9` | Move focused window to workspace 1-9 **without** shifting camera focus. |
| `Alt + Ctrl + 1` to `9` | `move --workspace 1-9` + focus | Move focused window to workspace 1-9 **and** immediately shift focus to it. |
| `Alt + Shift + J` | `move --prev-workspace` | Move focused window to the previous workspace. |
| `Alt + Shift + K` | `move --next-workspace` | Move focused window to the next workspace. |
| `Alt + Shift + A` | `move-workspace --dir left` | Shift the current workspace's parent container to the left monitor. |
| `Alt + Shift + F` | `move-workspace --dir right`| Shift the current workspace's parent container to the right monitor. |
| `Alt + Shift + D` | `move-workspace --dir up`   | Shift the current workspace's parent container to the top monitor. |
| `Alt + Shift + S` | `move-workspace --dir down` | Shift the current workspace's parent container to the bottom monitor. |

### 3. Window States, Gaps & Sizing
| Shortcut | Action / Command | Description |
| :--- | :--- | :--- |
| `Alt + Space` | `toggle-floating --centered`| Toggle focused window between Tiling and Centered Floating. |
| `Alt + T` | `toggle-tiling` | Return the focused window to a tiling state. |
| `Alt + F` | `toggle-fullscreen` | Toggle fullscreen mode for the focused window. |
| `Alt + N` | `toggle-minimized` | Minimize the focused window. |
| `Alt + Shift + Space` | `toggle-tiling-direction` | Toggle local split direction (Horizontal / Vertical) for new tiles. |
| `Alt + H` | `resize --width -5%` | Decrease width of tiling window by 5%. |
| `Alt + L` | `resize --width +5%` | Increase width of tiling window by 5%. |
| `Alt + U` | `resize --height +5%` | Increase height of tiling window by 5%. |
| `Alt + I` | `resize --height -5%` | Decrease height of tiling window by 5%. |

### 4. Interactive Resize Mode
Press **`Alt + Y`** to enter the interactive **Resize Mode**. This overrides standard bindings, allowing keyboard resizing using direction keys:
* `H` or `Left Arrow`: Decrease width by 2%
* `L` or `Right Arrow`: Increase width by 2%
* `K` or `Up Arrow`: Increase height by 2%
* `J` or `Down Arrow`: Decrease height by 2%
* Press **`Escape`** or **`Enter`** to exit Resize Mode.

### 5. Application Launchers & System Commands
| Shortcut | Action / Command | Launched Target / Script |
| :--- | :--- | :--- |
| `Alt + Enter` | Command Line / Shell | Windows Terminal (`wt`) |
| `Alt + B` | Web Browser | Firefox (`firefox.exe`) |
| `Alt + E` | File Manager | File Explorer (`explorer.exe`) |
| `Alt + O` | Note-taking | Obsidian (`obsidian.exe`) |
| `Alt + C` | Editor | Cursor (`cursor`) |
| `Alt + R` | Global App Launcher | Flow Launcher (`Flow.Launcher.exe`) |
| `Ctrl+Alt+Shift+Up`| Display Scaling Up | Custom powershell utility (`change_scale.ps1 up`) |
| `Ctrl+Alt+Shift+Down`| Display Scaling Down | Custom powershell utility (`change_scale.ps1 down`) |

### 6. Autotiling Layout Cycle
These shortcuts communicate directly with the background autotiler engine `glaze_autotile.py` to change tiling layouts:
* **`Ctrl + Alt + Space`**: Cycle forward to the next autotiling layout (`fair` ➔ `fair_horizontal` ➔ `columns` ➔ `rows`).
* **`Ctrl + Alt + Shift + Space`**: Cycle backward to the previous autotiling layout.

### 7. GlazeWM Management Hotkeys
* **`Alt + Q`**: Close the focused window.
* **`Alt + Shift + R`**: Reload GlazeWM configuration (`wm-reload-config`).
* **`Alt + Shift + W`**: Redraw all windows (`wm-redraw`).
* **`Alt + Shift + P`**: Toggle Pause / Resume GlazeWM (temporarily suspends/enables window tiling and hotkeys, useful for gaming or full-screen apps).
* **`Alt + Shift + Backspace`**: Restart GlazeWM process using local helper script `glaze-restart.bat`.
* **`Alt + Shift + E`**: Exit GlazeWM and close the window manager interface.

---

## 🛠️ Dynamic Autotiling Architecture (`glaze_autotile.py`)

The layout script acts as an IPC intermediary connecting to GlazeWM over local websockets (port `6123`).

### How It Works:
1. When launched, the script registers subscriptions for workspace events (`window_managed`, `window_unmanaged`, `focus_changed`, etc.).
2. When windows are opened or repositioned, the script calculates layouts:
   - **`fair`**: Divides screen real estate into a balanced grid based on window count (similar to AwesomeWM's fair layout).
   - **`fair_horizontal`**: Same grid math, prioritizing horizontal columns first.
   - **`columns` / `rows`**: Forces purely vertical or horizontal tiling splits.
3. If layout mode is set to exact fair, windows are set to `floating` and repositioned precisely with strict gap alignments.
4. **State Storage**:
   - Save path: `%USERPROFILE%\.glzr\glazewm\autotile_state.json` (holds layout details and controlled floating IDs).
   - Zebar synchronization path: `%USERPROFILE%\AppData\Roaming\zebar\downloads\glzr-io.starter@0.0.0\layout-state.json` (helps Zebar read and display current layout mode).

---

## 🖥️ Interactive Display Scaling (DPI Toggle)

Most tiling setups do not allow changing display scaling easily without navigating deep into Windows Settings. This configuration includes an automated, hotkey-driven DPI scaling switcher.

### Keybindings:
* **`Ctrl + Alt + Shift + Up`**: Increase display scaling.
* **`Ctrl + Alt + Shift + Down`**: Decrease display scaling.

### Supported Scaling Levels:
Cycles dynamically through: `100%` ➔ `125%` ➔ `150%` ➔ `175%` ➔ `200%`.

### How it Works:
1. When you trigger the hotkey, GlazeWM executes `change_scale.ps1` with the argument `up` or `down`.
2. The script queries your primary monitor's current scaling factor using the precompiled `SetDpi.exe` tool.
3. It finds the next/previous scaling percentage in the supported levels array and sets it instantly using `SetDpi.exe <percentage>`.

---

## 🚀 Setup & Installation Instructions

You can install this configuration environment in one of two ways:

### Method 1: Web Installer (Quickest)
Open PowerShell and run this single command to automatically download, install dependencies, copy configurations, and tailor user paths:
```powershell
irm https://raw.githubusercontent.com/tolgaozisik/glazewm-zebar-config/main/install.ps1 | iex
```

### Method 2: Local Installer (From Clone)
If you have cloned the repository locally:
1. Open PowerShell inside the repository root directory.
2. Run the installer script:
   ```powershell
   .\install.ps1
   ```

---

## 🎨 Layout & UI Design Features

* **Focused Border Styling**: Focused windows are highlighted using a clean `#00d7ff` (cyan) border (`2px` thickness) for high visibility on dark backgrounds.
* **Workspace Gap Management**:
  - `inner_gap`: `2px` (tiling separation).
  - `outer_gap`: Top is set to `43px` to make room for the Zebar status bar; bottom, left, and right outer gaps are set to `2px`.
* **Zebar Styling**: The customized starter pack renders with modern Google Sans fonts, showcasing virtual desktop numbers, hardware metrics, active layout status, time, and custom icon alignments.

---

## 🔍 Troubleshooting & Common Issues

### 1. Zebar shows a blank bar or is missing widgets
* Make sure Zebar is installed via winget (`winget install glzr-io.zebar`).
* Verify that you ran the `install.ps1` script to populate the folder `%USERPROFILE%\AppData\Roaming\zebar\downloads\glzr-io.starter@0.0.0`.
* Check `%USERPROFILE%\.glzr\zebar\settings.json` to verify that the startup config is pointed to `glzr-io.starter` and `with-glazewm`.

### 2. Autotiler layouts do not cycle (`Ctrl + Alt + Space` does nothing)
* Ensure Python is installed (`python --version`) and is in your system `PATH`. Reinstall it using `winget install Python.Python.3.11` if missing.
* Ensure the `websockets` Python library is installed. Run: `pip install websockets` in your terminal.
* Inspect the autotiler logs for details: `%USERPROFILE%\.glzr\glazewm\autotile.log` and `%USERPROFILE%\.glzr\glazewm\errors.log`.

### 3. Display scaling hotkeys (`Ctrl+Alt+Shift+Up/Down`) do not change scaling
* Test if the SetDpi utility runs on your machine. Open PowerShell and run:
  ```powershell
  & "$env:USERPROFILE\bin\SetDpi.exe" get
  ```
* If it returns your current scaling (e.g. `125`), it is working. Make sure your execution policy allows executing the local powershell script: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

---

## 🤝 Credits & Acknowledgements

This configuration setup utilizes the following open-source utility for Windows display scaling control:
* **[SetDPI](https://github.com/imniko/SetDPI)** by **[imniko](https://github.com/imniko)**: A lightweight CLI tool that allows changing Windows display scaling settings per monitor. The precompiled executable is bundled inside the `bin/` directory for installation convenience.


