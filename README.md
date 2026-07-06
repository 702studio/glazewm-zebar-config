# Windows Customization Setup: GlazeWM & Zebar Configurations

This repository contains my personal, custom configurations for [GlazeWM](https://github.com/glzr-io/glazewm) (tiling window manager) and [Zebar](https://github.com/glzr-io/zebar) (customizable desktop status bar) on Windows. It includes a custom autotiler python script to replicate AwesomeWM-style fair/columns/rows layout behavior.

Designed to be **Agent-Friendly** (fully automated installation scripts and clear structure for AI assistants).

---

## Directory Structure

```
.
├── glazewm/
│   └── config.yaml               # GlazeWM main configuration (hotkeys, workspace, gaps)
├── zebar/
│   ├── settings.json             # Zebar main settings (defines active packs/presets)
│   └── packs/
│       └── glzr-io.starter/     # Custom Zebar widgets and bar design
│           ├── styles.css        # Customized styles for the bar
│           ├── with-glazewm.html # customized HTML structure for GlazeWM widgets
│           └── zpack.json        # Widget pack configuration metadata
└── glaze_autotile.py             # Python script for AwesomeWM-style autotiling logic
```

---

## Custom Features

1. **AwesomeWM-Style Autotiling (`glaze_autotile.py`)**:
   - Runs in the background via local websockets to GlazeWM (port `6123`).
   - Supports `fair`, `fair_horizontal`, `columns`, and `rows` layout modes.
   - Saves layout state to `~/.glzr/glazewm/autotile_state.json` and syncs with Zebar layouts dynamically.
   - Includes custom popup/toast alerts when changing layout.

2. **Gaps & Visual Effects**:
   - Thin outer gaps (`2px`), slightly taller top gap (`43px`) to accommodate the top status bar.
   - Cyan/light blue focused border (`#00d7ff`) to make focused windows pop out.
   - Workspace rules to keep background hook processes separate from primary workspaces.

3. **Zebar Integration**:
   - Displays workspace name, active layout, date/time, hardware specs, and other essential metrics.
   - Styled with a dark glassmorphic accent and clean modern fonts.

---

## Automatic Installation (PowerShell)

Open PowerShell as an administrator or user, and run the following script block to install all configurations automatically:

```powershell
# 1. Create necessary configuration folders
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.glzr\glazewm"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.glzr\zebar"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\AppData\Roaming\zebar\downloads\glzr-io.starter@0.0.0"

# 2. Copy glaze_autotile.py to your user directory
Copy-Item "glaze_autotile.py" "$env:USERPROFILE\glaze_autotile.py" -Force

# 3. Copy GlazeWM configuration
Copy-Item "glazewm\config.yaml" "$env:USERPROFILE\.glzr\glazewm\config.yaml" -Force

# 4. Copy Zebar settings
Copy-Item "zebar\settings.json" "$env:USERPROFILE\.glzr\zebar\settings.json" -Force

# 5. Copy Zebar Pack Files
Copy-Item -Path "zebar\packs\glzr-io.starter\*" -Destination "$env:USERPROFILE\AppData\Roaming\zebar\downloads\glzr-io.starter@0.0.0\" -Recurse -Force
```

---

## Dependencies & Requirements

To run this layout engine smoothly, ensure you have:

1. **GlazeWM v3+ & Zebar v3+** installed on Windows.
2. **Python 3.10+** added to `PATH`.
3. **Python websockets** module installed. Run:
   ```bash
   pip install websockets
   ```
4. `pythonw.exe` will be used automatically by GlazeWM startup commands to run the autotiler silently in the background without spawning terminal windows.

---

## Controls & Hotkeys

For full hotkeys, check the [config.yaml](file:///./glazewm/config.yaml). Main highlights:
- `Alt + J`: Previous workspace
- `Alt + K`: Next workspace
- `Alt + Up/Down/Left/Right`: Focus navigation
- `Alt + Shift + Up/Down/Left/Right`: Swap/Move window
- Autotiling automatically manages splitting layout direction.
