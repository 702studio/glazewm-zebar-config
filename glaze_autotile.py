import asyncio
import argparse
import json
import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import websockets


HOME = Path.home()
LOG_DIR = HOME / ".glzr" / "glazewm"
STATE_FILE = LOG_DIR / "autotile_state.json"
ZEBAR_LAYOUT_STATE_FILE = HOME / "AppData" / "Roaming" / "zebar" / "downloads" / "glzr-io.starter@0.0.0" / "layout-state.json"

DEFAULT_CONFIG = {
    "core": {
        "ws_uri": "ws://localhost:6123",
        "debounce_delay_ms": 160,
        "reconnect_delay_ms": 1200,
        "log_file": str(LOG_DIR / "autotile.log"),
    },
    "layout": {
        # GlazeWM does not have native custom layouts. This script guides the
        # next split for every tiled leaf. For AwesomeWM fair layouts, it can
        # also place windows exactly as managed floating windows.
        "default_mode": "fair",
        "modes": ["fair", "fair_horizontal", "columns", "rows"],
        "exact_fair": True,
        "exact_gap_px": 2,
        "aspect_deadzone": 0.12,
        "apply_to_all_tiling_windows": True,
    },
    "state": {
        "file": str(STATE_FILE),
        "zebar_file": str(ZEBAR_LAYOUT_STATE_FILE),
    },
}


@dataclass(frozen=True)
class Window:
    id: str
    parent_id: str
    width: int
    height: int
    x: int
    y: int
    has_focus: bool
    title: str
    process_name: str
    state_type: str

    @classmethod
    def from_dict(cls, data: dict) -> "Window":
        state = data.get("state", {})
        state_type = state.get("type") if isinstance(state, dict) else state
        return cls(
            id=data.get("id", ""),
            parent_id=data.get("parentId", ""),
            width=int(data.get("width", 0) or 0),
            height=int(data.get("height", 0) or 0),
            x=int(data.get("x", 0) or 0),
            y=int(data.get("y", 0) or 0),
            has_focus=bool(data.get("hasFocus", False)),
            title=data.get("title", "") or "",
            process_name=data.get("processName", "") or "",
            state_type=state_type or "",
        )

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    width: int
    height: int
    x: int
    y: int
    children: List[Dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict) -> "Workspace":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            width=int(data.get("width", 0) or 0),
            height=int(data.get("height", 0) or 0),
            x=int(data.get("x", 0) or 0),
            y=int(data.get("y", 0) or 0),
            children=data.get("children", []) or [],
        )

    def get_tiling_windows(self) -> List[Window]:
        wins: List[Window] = []

        def traverse(nodes: Iterable[Dict[str, Any]]) -> None:
            for node in nodes:
                node_type = node.get("type")
                if node_type == "window":
                    state = node.get("state", {})
                    state_type = state.get("type") if isinstance(state, dict) else state
                    if state_type == "tiling" and node.get("displayState") != "hidden":
                        wins.append(Window.from_dict(node))
                elif node.get("children"):
                    traverse(node.get("children") or [])

        traverse(self.children)
        return wins

    def get_layout_windows(self, controlled_ids: Iterable[str]) -> List[Window]:
        controlled = set(controlled_ids)
        wins: List[Window] = []

        def traverse(nodes: Iterable[Dict[str, Any]]) -> None:
            for node in nodes:
                node_type = node.get("type")
                if node_type == "window":
                    if node.get("displayState") == "hidden":
                        continue
                    win = Window.from_dict(node)
                    if win.state_type == "tiling" or win.id in controlled:
                        wins.append(win)
                elif node.get("children"):
                    traverse(node.get("children") or [])

        traverse(self.children)
        return wins


class SingleInstance:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self) -> "SingleInstance":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "a+b")
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise SystemExit(0)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self.handle:
            return
        if os.name == "nt":
            import msvcrt

            try:
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        self.handle.close()


class GlazeWMClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.ws: Any = None
        self.message_queue: asyncio.Queue[str] = asyncio.Queue()

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and getattr(self.ws, "state", None) == websockets.protocol.State.OPEN

    async def connect(self) -> None:
        self.ws = await websockets.connect(self.uri)
        asyncio.create_task(self._receive_loop())

    async def close(self) -> None:
        if self.ws:
            await self.ws.close()
        self.ws = None

    async def _receive_loop(self) -> None:
        if not self.ws:
            return
        try:
            async for msg in self.ws:
                await self.message_queue.put(msg)
        except Exception as exc:
            logging.debug("receive loop stopped: %s", exc)

    async def send_command(self, cmd: str) -> None:
        if self.is_connected:
            await self.ws.send(f"command {cmd}")

    async def query(self, query_str: str, timeout: float = 1.2) -> dict:
        if not self.is_connected:
            return {}
        await self.ws.send(query_str)
        while True:
            try:
                msg = await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
                event_data = json.loads(msg)
                if (
                    event_data.get("messageType") == "client_response"
                    and event_data.get("clientMessage") == query_str
                ):
                    return event_data
            except asyncio.TimeoutError:
                logging.debug("query timed out: %s", query_str)
                return {}
            except Exception as exc:
                logging.debug("query failed: %s", exc)
                return {}


class AutoTilerApp:
    def __init__(self, config: dict, enable_stats: bool = True):
        self.config = config
        self.enable_stats = enable_stats
        self.client = GlazeWMClient(config["core"]["ws_uri"])
        self.window_dirs: Dict[str, str] = {}
        self.stats: Dict[str, Any] = {"total_guidance": 0}
        self.state_file = Path(config["state"]["file"])
        self.layout_mode = self._read_layout_mode()
        self.controlled_floating_ids = self._read_controlled_floating_ids()

        if self.enable_stats and os.path.exists("auto_tiler_stats.json"):
            try:
                with open("auto_tiler_stats.json", "r", encoding="utf-8") as f:
                    self.stats.update(json.load(f))
            except Exception as exc:
                logging.debug("stats load failed: %s", exc)

    def save_stats(self) -> None:
        if not self.enable_stats:
            return
        try:
            with open("auto_tiler_stats.json", "w", encoding="utf-8") as f:
                json.dump(self.stats, f)
        except Exception as exc:
            logging.debug("stats save failed: %s", exc)

    async def run_forever(self) -> None:
        reconnect = self.config["core"]["reconnect_delay_ms"] / 1000.0
        while True:
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("autotiler loop crashed")
            finally:
                self.save_stats()
                await self.client.close()

            await asyncio.sleep(reconnect)
            self.client = GlazeWMClient(self.config["core"]["ws_uri"])

    async def _run_once(self) -> None:
        await self.client.connect()
        for ev in [
            "window_managed",
            "window_unmanaged",
            "focus_changed",
            "workspace_activated",
            "focused_container_moved",
            "tiling_direction_changed",
        ]:
            await self.client.ws.send(f"sub -e {ev}")

        await self._apply_guidance("startup")

        debounce = self.config["core"]["debounce_delay_ms"] / 1000.0
        while self.client.is_connected:
            try:
                msg = await asyncio.wait_for(self.client.message_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            try:
                event_data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            if event_data.get("messageType") not in (
                "event_subscription",
                "event_subscription_message",
            ):
                continue

            event_type = event_data.get("data", {}).get("eventType", "unknown")
            await asyncio.sleep(debounce)
            while not self.client.message_queue.empty():
                try:
                    self.client.message_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            await self._apply_guidance(event_type)

    async def _apply_guidance(self, event_type: str) -> None:
        self._drain_queue()
        self.layout_mode = self._read_layout_mode()
        self.controlled_floating_ids = self._read_controlled_floating_ids()
        res = await self.client.query("query workspaces")
        workspaces = res.get("data", {}).get("workspaces", [])
        active_ws_data = next((w for w in workspaces if w.get("hasFocus")), None)
        if not active_ws_data:
            return

        live_ids = self._workspace_window_ids(workspaces)
        stale_controlled = self.controlled_floating_ids - live_ids
        if stale_controlled:
            self.controlled_floating_ids -= stale_controlled
            self._write_controlled_floating_ids(self.controlled_floating_ids)

        ws = Workspace.from_dict(active_ws_data)
        if self._uses_exact_fair(self.layout_mode):
            await self._apply_exact_fair(ws, self.layout_mode, event_type)
            return

        await self._release_exact_fair_control(live_ids)
        wins = ws.get_tiling_windows()
        live_tiling_ids = {w.id for w in wins}
        for stale_id in list(self.window_dirs):
            if stale_id not in live_tiling_ids:
                self.window_dirs.pop(stale_id, None)

        if not wins:
            await self.client.send_command("set-tiling-direction horizontal")
            return

        targets = wins if self.config["layout"]["apply_to_all_tiling_windows"] else [self._focused_or_largest(wins)]
        changed = 0
        for win in targets:
            direction = self._desired_direction(ws, win, wins, self.layout_mode)
            if self.window_dirs.get(win.id) == direction:
                continue
            await self.client.send_command(f"--id {win.id} set-tiling-direction {direction}")
            self.window_dirs[win.id] = direction
            changed += 1

        if changed:
            logging.info(
                "%s: workspace=%s windows=%s updated_dirs=%s",
                event_type,
                ws.name,
                len(wins),
                changed,
                extra={"layout_mode": self.layout_mode},
            )
            self._bump_stats(changed)

    def set_layout_mode(self, mode: str) -> str:
        self.layout_mode = self._normalize_layout_mode(mode)
        self._write_layout_mode(self.layout_mode)
        self.window_dirs.clear()
        return self.layout_mode

    def cycle_layout_mode(self, step: int) -> str:
        modes = self._layout_modes()
        current = self._read_layout_mode()
        try:
            current_index = modes.index(current)
        except ValueError:
            current_index = 0

        self.layout_mode = modes[(current_index + step) % len(modes)]
        self._write_layout_mode(self.layout_mode)
        self.window_dirs.clear()
        return self.layout_mode

    def _layout_modes(self) -> List[str]:
        modes = self.config["layout"].get("modes", [])
        return [str(mode) for mode in modes] or ["fair"]

    def _normalize_layout_mode(self, mode: Optional[str]) -> str:
        aliases = {
            "auto": "fair",
            "grid": "fair",
            "smart_grid": "fair",
            "fair-horizontal": "fair_horizontal",
            "horizontal_fair": "fair_horizontal",
            "column": "columns",
            "vertical_columns": "columns",
            "row": "rows",
            "horizontal_rows": "rows",
        }
        normalized = (mode or "").strip().lower().replace(" ", "_")
        normalized = aliases.get(normalized, normalized)
        modes = self._layout_modes()
        if normalized in modes:
            return normalized
        return str(self.config["layout"].get("default_mode", modes[0]))

    def _read_layout_mode(self) -> str:
        data = self._read_state()
        return self._normalize_layout_mode(data.get("layout_mode"))

    def _write_layout_mode(self, mode: str) -> None:
        data = self._read_state()
        data["layout_mode"] = mode
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_state(data)

    def _read_controlled_floating_ids(self) -> set[str]:
        data = self._read_state()
        raw_ids = data.get("controlled_floating_ids", [])
        if not isinstance(raw_ids, list):
            return set()
        return {str(item) for item in raw_ids}

    def _write_controlled_floating_ids(self, ids: Iterable[str]) -> None:
        data = self._read_state()
        data["controlled_floating_ids"] = sorted({str(item) for item in ids})
        self._write_state(data)

    def _read_state(self) -> dict:
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {"layout_mode": self.config["layout"].get("default_mode")}
        except Exception as exc:
            logging.debug("layout state load failed: %s", exc)
            return {"layout_mode": self.config["layout"].get("default_mode")}

    def _write_state(self, data: dict) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._write_zebar_layout_state(data)
        except Exception as exc:
            logging.debug("layout state save failed: %s", exc)

    def _write_zebar_layout_state(self, data: dict) -> None:
        try:
            zebar_file = Path(self.config["state"]["zebar_file"])
            zebar_file.parent.mkdir(parents=True, exist_ok=True)
            layout_mode = self._normalize_layout_mode(data.get("layout_mode"))
            payload = {
                "layout_mode": layout_mode,
                "display_name": layout_mode.replace("_", " "),
                "updated_at": data.get("updated_at") or datetime.now().isoformat(timespec="seconds"),
            }
            with open(zebar_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:
            logging.debug("zebar layout state save failed: %s", exc)

    def _uses_exact_fair(self, mode: str) -> bool:
        return bool(self.config["layout"].get("exact_fair")) and mode in {"fair", "fair_horizontal"}

    async def _apply_exact_fair(self, ws: Workspace, mode: str, event_type: str) -> None:
        wins = ws.get_layout_windows(self.controlled_floating_ids)
        if not wins:
            await self.client.send_command("set-tiling-direction horizontal")
            return

        ordered_wins = self._fair_window_order(wins, horizontal=(mode == "fair_horizontal"))
        geometries = self._fair_geometries(ws, len(ordered_wins), horizontal=(mode == "fair_horizontal"))
        focused_id = next((w.id for w in ordered_wins if w.has_focus), None)

        changed = 0
        for win, geom in zip(ordered_wins, geometries):
            if self._geometry_matches(win, geom):
                continue
            if win.state_type != "floating":
                await self.client.send_command(f"--id {win.id} set-floating --centered=false")
            await self.client.send_command(
                f"--id {win.id} size --width {geom['width']} --height {geom['height']}"
            )
            await self.client.send_command(
                f"--id {win.id} position --x-pos {geom['x']} --y-pos {geom['y']}"
            )
            changed += 1

        self.controlled_floating_ids |= {w.id for w in ordered_wins}
        self._write_controlled_floating_ids(self.controlled_floating_ids)
        self.window_dirs.clear()

        if focused_id and changed:
            await self.client.send_command(f"focus --container-id {focused_id}")

        if changed or event_type in {"startup", "layout_command", "window_managed", "window_unmanaged"}:
            logging.info(
                "%s: exact_fair=%s workspace=%s windows=%s positioned=%s",
                event_type,
                mode,
                ws.name,
                len(ordered_wins),
                changed,
            )

    async def _release_exact_fair_control(self, live_ids: set[str]) -> None:
        if not self.controlled_floating_ids:
            return

        released = 0
        for window_id in sorted(self.controlled_floating_ids & live_ids):
            await self.client.send_command(f"--id {window_id} set-tiling")
            released += 1

        self.controlled_floating_ids.clear()
        self._write_controlled_floating_ids(self.controlled_floating_ids)
        if released:
            logging.info("released exact fair control for %s windows", released)

    def _workspace_window_ids(self, workspaces: List[Dict[str, Any]]) -> set[str]:
        ids: set[str] = set()

        def traverse(nodes: Iterable[Dict[str, Any]]) -> None:
            for node in nodes:
                if node.get("type") == "window":
                    window_id = node.get("id")
                    if window_id:
                        ids.add(str(window_id))
                elif node.get("children"):
                    traverse(node.get("children") or [])

        for workspace in workspaces:
            traverse(workspace.get("children", []) or [])
        return ids

    @staticmethod
    def _fair_window_order(wins: List[Window], horizontal: bool = False) -> List[Window]:
        if horizontal:
            return sorted(wins, key=lambda w: (w.y, w.x, w.title, w.id))
        return sorted(wins, key=lambda w: (w.x, w.y, w.title, w.id))

    def _fair_geometries(self, ws: Workspace, count: int, horizontal: bool = False) -> List[Dict[str, int]]:
        if count <= 0:
            return []

        work_x, work_y = ws.x, ws.y
        work_width, work_height = ws.width, ws.height
        if horizontal:
            work_x, work_y = work_y, work_x
            work_width, work_height = work_height, work_width

        if count == 2:
            rows, cols = 1, 2
        else:
            rows = math.ceil(math.sqrt(count))
            cols = math.ceil(count / rows)

        gap = int(self.config["layout"].get("exact_gap_px", 0) or 0)
        geometries: List[Dict[str, int]] = []
        for index in range(count):
            row = index % rows
            col = math.floor(index / rows)

            if index >= rows * cols - rows:
                local_rows = count - (rows * cols - rows)
            else:
                local_rows = rows
            local_cols = cols

            if row == local_rows - 1:
                height = work_height - math.ceil(work_height / local_rows) * row
                y_pos = work_height - height
            else:
                height = math.ceil(work_height / local_rows)
                y_pos = height * row

            if col == local_cols - 1:
                width = work_width - math.ceil(work_width / local_cols) * col
                x_pos = work_width - width
            else:
                width = math.ceil(work_width / local_cols)
                x_pos = width * col

            x_pos += work_x
            y_pos += work_y

            if horizontal:
                x_pos, y_pos = y_pos, x_pos
                width, height = height, width

            geometries.append(
                {
                    "x": int(round(x_pos + gap)),
                    "y": int(round(y_pos + gap)),
                    "width": max(1, int(round(width - (2 * gap)))),
                    "height": max(1, int(round(height - (2 * gap)))),
                }
            )

        return geometries

    @staticmethod
    def _geometry_matches(win: Window, geom: Dict[str, int], tolerance: int = 3) -> bool:
        return (
            abs(win.x - geom["x"]) <= tolerance
            and abs(win.y - geom["y"]) <= tolerance
            and abs(win.width - geom["width"]) <= tolerance
            and abs(win.height - geom["height"]) <= tolerance
            and win.state_type == "floating"
        )

    def _desired_direction(self, ws: Workspace, win: Window, wins: List[Window], mode: str) -> str:
        if mode == "columns":
            return "horizontal"
        if mode == "rows":
            return "vertical"
        if mode == "fair_horizontal":
            return self._opposite_direction(self._desired_fair_direction(ws, win, wins))
        return self._desired_fair_direction(ws, win, wins)

    def _desired_fair_direction(self, ws: Workspace, win: Window, wins: List[Window]) -> str:
        count = len(wins)
        if count <= 1:
            return "horizontal"

        if count == 2:
            other = next((w for w in wins if w.id != win.id), None)
            if other:
                if self._mostly_same_row(win, other):
                    return "vertical"
                if self._mostly_same_column(win, other):
                    return "horizontal"

        if self._spans_height_column(ws, win):
            return "vertical"
        if self._spans_width_row(ws, win):
            return "horizontal"

        ratio = win.width / win.height if win.height > 0 else 1.0
        deadzone = float(self.config["layout"]["aspect_deadzone"])

        if ratio > 1.0 + deadzone:
            return "horizontal"
        if ratio < 1.0 - deadzone:
            return "vertical"

        # Near-square cells get a stable tie-breaker based on the overall
        # workspace shape and cell position. This avoids oscillating directions.
        if ws.width >= ws.height * 1.25:
            return "vertical" if count <= 3 else "horizontal"
        return "horizontal" if win.x < ws.x + (ws.width / 2) else "vertical"

    @staticmethod
    def _opposite_direction(direction: str) -> str:
        return "vertical" if direction == "horizontal" else "horizontal"

    @staticmethod
    def _focused_or_largest(wins: List[Window]) -> Window:
        return next((w for w in wins if w.has_focus), max(wins, key=lambda w: w.area))

    @staticmethod
    def _mostly_same_row(a: Window, b: Window) -> bool:
        y_close = abs(a.y - b.y) <= max(24, min(a.height, b.height) * 0.08)
        height_close = abs(a.height - b.height) <= max(24, max(a.height, b.height) * 0.12)
        return y_close and height_close

    @staticmethod
    def _mostly_same_column(a: Window, b: Window) -> bool:
        x_close = abs(a.x - b.x) <= max(24, min(a.width, b.width) * 0.08)
        width_close = abs(a.width - b.width) <= max(24, max(a.width, b.width) * 0.12)
        return x_close and width_close

    @staticmethod
    def _spans_height_column(ws: Workspace, win: Window) -> bool:
        return win.height >= ws.height * 0.72 and win.width <= ws.width * 0.72

    @staticmethod
    def _spans_width_row(ws: Workspace, win: Window) -> bool:
        return win.width >= ws.width * 0.72 and win.height <= ws.height * 0.72

    def _bump_stats(self, amount: int) -> None:
        if not self.enable_stats:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        self.stats["TotalSwitches"] = int(self.stats.get("TotalSwitches", 0)) + amount
        self.stats["total_guidance"] = int(self.stats.get("total_guidance", 0)) + amount

        daily = self.stats.get("DailySwitches", {})
        if not isinstance(daily, dict):
            daily = {}
        daily[today] = int(daily.get(today, 0)) + amount
        self.stats["DailySwitches"] = daily

        if self.stats["total_guidance"] % 10 == 0:
            self.save_stats()

    def _drain_queue(self) -> None:
        while not self.client.message_queue.empty():
            try:
                self.client.message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


def setup_logging(config: dict) -> None:
    log_file = Path(config["core"]["log_file"])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_file),
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def show_layout_toast(mode: str, duration_ms: int = 1200) -> None:
    try:
        import tkinter as tk
    except Exception as exc:
        logging.debug("layout toast unavailable: %s", exc)
        return

    try:
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-alpha", 0.94)
        except tk.TclError:
            pass

        label = tk.Label(
            root,
            text=f"Glaze layout: {mode.replace('_', ' ')}",
            bg="#101820",
            fg="#f5f7fa",
            padx=18,
            pady=10,
            font=("Segoe UI", 12, "bold"),
        )
        label.pack()
        root.update_idletasks()

        width = root.winfo_width()
        height = root.winfo_height()
        x = max(0, root.winfo_screenwidth() - width - 28)
        y = 64
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.after(duration_ms, root.destroy)
        root.mainloop()
    except Exception as exc:
        logging.debug("layout toast failed: %s", exc)


async def run_layout_command(config: dict, args: argparse.Namespace) -> None:
    app = AutoTilerApp(config, enable_stats=False)
    if args.layout_next:
        mode = app.cycle_layout_mode(1)
    elif args.layout_prev:
        mode = app.cycle_layout_mode(-1)
    elif args.layout:
        mode = app.set_layout_mode(args.layout)
    else:
        mode = app._read_layout_mode()

    try:
        await app.client.connect()
    except Exception as exc:
        logging.info("layout mode saved as %s; live apply skipped: %s", mode, exc)
        print(f"layout_mode={mode}")
        if not args.no_toast:
            show_layout_toast(mode)
        return

    try:
        await app._apply_guidance("layout_command")
    finally:
        await app.client.close()

    print(f"layout_mode={app.layout_mode}")
    if not args.no_toast:
        show_layout_toast(app.layout_mode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Guide GlazeWM tiling directions toward AwesomeWM-style layouts.")
    parser.add_argument("--no-stats", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--layout-next", action="store_true")
    group.add_argument("--layout-prev", action="store_true")
    group.add_argument("--layout")
    parser.add_argument("--apply-now", action="store_true")
    parser.add_argument("--no-toast", action="store_true")
    args = parser.parse_args()

    setup_logging(DEFAULT_CONFIG)
    if args.layout_next or args.layout_prev or args.layout or args.apply_now:
        asyncio.run(run_layout_command(DEFAULT_CONFIG, args))
        return

    enable_stats = not args.no_stats
    lock_path = LOG_DIR / "autotile.lock"
    with SingleInstance(lock_path):
        app = AutoTilerApp(DEFAULT_CONFIG, enable_stats=enable_stats)
        try:
            asyncio.run(app.run_forever())
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
