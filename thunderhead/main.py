import os
import sys
import subprocess
import webbrowser

from thunderhead.config import load_config, DATA_DIR
from thunderhead.server.setup import run_setup
from thunderhead.server.tray import run_tray


def start_server(config: dict) -> subprocess.Popen:
    port = config["port"]
    cert = os.path.join(DATA_DIR, "cert.pem")
    key = os.path.join(DATA_DIR, "key.pem")

    env = os.environ.copy()
    env["THUNDERHEAD_CONFIG"] = os.path.join(DATA_DIR, "config.json")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "thunderhead.server.app:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--ssl-certfile", cert,
        "--ssl-keyfile", key,
        "--log-level", "info",
    ]

    proc = subprocess.Popen(cmd, env=env)
    return proc


def main():
    config = load_config()
    if not config or not config.get("configured"):
        config = run_setup()

    proc = start_server(config)
    print(f"  Thunderhead running at https://localhost:{config['port']}")
    print(f"  VPS Storage: {config['storage_root']}")
    print("  Check the system tray for controls")

    webbrowser.open(f"https://localhost:{config['port']}")

    run_tray(config, proc)


if __name__ == "__main__":
    main()
