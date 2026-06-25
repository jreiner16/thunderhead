from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Button, Label, Static
from textual.containers import Container
from textual import events

from thunderhead.client.api import ThunderheadClient


def format_size(bytes: int) -> str:
    if bytes == 0:
        return "-"
    units = ["B", "KB", "MB", "GB"]
    i = min(int(bytes.bit_length() / 10), len(units) - 1)
    return f"{bytes / (1024 ** i):.1f} {units[i]}" if i > 0 else f"{bytes} B"


def format_date(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def icon_for(name: str) -> str:
    ext = name.split(".")[-1].lower() if "." in name else ""
    icons = {
        "txt": "\U0001f4c4", "md": "\U0001f4c4", "json": "\U0001f4c4",
        "py": "\U0001f40d", "js": "\U0001f4dc", "ts": "\U0001f4dc",
        "html": "\U0001f310", "css": "\U0001f3a8",
        "jpg": "\U0001f5bc", "png": "\U0001f5bc", "gif": "\U0001f5bc",
        "zip": "\U0001f4e6", "tar": "\U0001f4e6", "gz": "\U0001f4e6",
        "pdf": "\U0001f4d5",
    }
    return icons.get(ext, "\U0001f4c4")


class ConnectScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Thunderhead Client", classes="client-title"),
            Static("Connect to your personal VPS", classes="client-subtitle"),
            Static("", classes="spacer"),
            Label("Server Address", classes="field-label"),
            Input(
                placeholder="192.168.1.42:8443",
                id="address",
                classes="field",
            ),
            Label("Password", classes="field-label"),
            Input(
                placeholder="Admin password",
                password=True,
                id="password",
                classes="field",
            ),
            Static("", classes="spacer"),
            Button("Connect", id="connect", variant="primary"),
            Static("", id="status", classes="client-status"),
            classes="connect-form",
        )

    def on_button_pressed(self, event: Button.Pressed):
        self._connect()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "password":
            self._connect()

    def _connect(self):
        address = self.query_one("#address", Input).value.strip()
        password = self.query_one("#password", Input).value
        status = self.query_one("#status", Static)

        if not address or not password:
            status.update("Enter address and password")
            return

        status.update("Connecting...")
        self.app.client = ThunderheadClient(address, password)

        async def do_connect():
            success = await self.app.client.login()
            if success:
                status.update("Connected! Loading files...")
                self.app.address_label = address
                self.app.push_screen("browser")
            else:
                status.update("Connection failed - check address and password")

        asyncio.create_task(do_connect())


class BrowserScreen(Screen):
    def __init__(self):
        super().__init__()
        self.current_path = "/"
        self.items: list[dict] = []
        self.cursor_index = 0

    def compose(self) -> ComposeResult:
        yield Container(
            Static("", id="header-bar", classes="browser-header"),
            Static("", id="file-list", classes="file-list"),
            Static("", id="footer-bar", classes="footer-bar"),
            classes="browser-layout",
        )

    def on_mount(self):
        self._refresh()

    async def _refresh(self):
        header = self.query_one("#header-bar", Static)
        header.update(f"  {self.app.address_label}  |  {self.current_path}")

        items = await self.app.client.list_files(self.current_path)
        if items is None:
            self._show_error("Connection lost")
            return

        self.items = items
        self.cursor_index = 0
        self._render_list()

    def _render_list(self):
        widget = self.query_one("#file-list", Static)
        lines = [""]
        has_parent = self.current_path != "/"

        if has_parent:
            marker = ">" if self.cursor_index == 0 else " "
            lines.append(f"  {marker}  [..]")

        for i, item in enumerate(self.items):
            idx = i + (1 if has_parent else 0)
            icon = "[D]" if item["is_dir"] else "[F]"
            size = "-" if item["is_dir"] else format_size(item["size"])
            date = format_date(item["modified"])
            marker = ">" if idx == self.cursor_index else " "
            name = item["name"]
            if len(name) > 28:
                name = name[:25] + "..."
            lines.append(f"  {marker} {icon}  {name:<28} {size:>8}  {date}")

        widget.update("\n".join(lines))

    def _show_error(self, msg: str):
        self.query_one("#file-list", Static).update(f"\n  [!] {msg}")

    async def _go_up(self):
        if self.current_path != "/":
            self.current_path = self.current_path.rstrip("/").rsplit("/", 1)[0] or "/"
            self.cursor_index = 0
            await self._refresh()

    async def _activate(self):
        has_parent = self.current_path != "/"
        idx = self.cursor_index - (1 if has_parent else 0)

        if has_parent and self.cursor_index == 0:
            await self._go_up()
            return

        if 0 <= idx < len(self.items):
            item = self.items[idx]
            if item["is_dir"]:
                self.current_path = item["path"]
                self.cursor_index = 0
                await self._refresh()

    def _quit(self):
        self.app.exit()

    def on_key(self, event: events.Key):
        if event.key == "q":
            self._quit()
        elif event.key == "up":
            has_parent = self.current_path != "/"
            max_idx = len(self.items) + (1 if has_parent else 0) - 1
            self.cursor_index = max(0, self.cursor_index - 1)
            self._render_list()
        elif event.key == "down":
            has_parent = self.current_path != "/"
            max_idx = len(self.items) + (1 if has_parent else 0) - 1
            self.cursor_index = min(max_idx, self.cursor_index + 1)
            self._render_list()
        elif event.key == "enter":
            asyncio.create_task(self._activate())
        elif event.key == "backspace":
            asyncio.create_task(self._go_up())


class ClientApp(App):
    CSS = """
    Screen {
        background: #0a0a0a;
    }
    Static, Label {
        color: #c0c0c0;
    }
    .client-title {
        text-style: bold;
        color: #c0c0c0;
    }
    .client-subtitle {
        color: #555;
    }
    .field-label {
        color: #666;
        margin-bottom: 1;
    }
    Input {
        background: #0a0a0a;
        color: #c0c0c0;
        border: solid #222;
    }
    Input:focus {
        border: solid #8ab4f8;
    }
    Button {
        background: #8ab4f8;
        color: #0a0a0a;
        border: none;
        text-style: bold;
    }
    Button:hover {
        background: #5a8ad4;
    }
    .client-status {
        color: #666;
    }
    .browser-header {
        color: #8ab4f8;
        padding: 1 0;
        background: #111;
    }
    .file-list {
        color: #c0c0c0;
        padding: 0 0;
    }
    .footer-bar {
        color: #555;
        padding: 1 0;
        background: #0a0a0a;
    }
    .spacer {
        height: 1;
    }
    .connect-form {
        align: center middle;
    }
    .browser-layout {
        layout: vertical;
    }
    """

    SCREENS = {
        "connect": ConnectScreen,
        "browser": BrowserScreen,
    }

    def __init__(self):
        super().__init__()
        self.client: ThunderheadClient | None = None
        self.address_label: str = ""

    def on_mount(self):
        self.push_screen("connect")


def run_client():
    app = ClientApp()
    app.run()
