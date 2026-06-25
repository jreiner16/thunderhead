import os
import sys
import webbrowser
import subprocess
import threading

import pystray
from PIL import Image, ImageDraw


def _create_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.polygon(
        [(32, 2), (12, 38), (28, 38), (18, 62), (52, 24), (34, 24), (44, 2)],
        fill=(138, 180, 248),
    )
    return img


def run_tray(config: dict, server_proc: subprocess.Popen, use_ssl: bool = True):
    port = config.get("port", 8443)
    proto = "https" if use_ssl else "http"
    url = f"{proto}://localhost:{port}"

    def on_open(_icon, _item):
        webbrowser.open(url)

    def on_quit(_icon, _item):
        _icon.stop()
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        os._exit(0)

    icon = pystray.Icon(
        "thunderhead",
        _create_icon_image(),
        "Thunderhead - Personal VPS",
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        ),
    )
    icon.run()
