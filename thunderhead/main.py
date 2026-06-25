import argparse
import os
import sys
import subprocess
import webbrowser

from thunderhead.config import load_config, DATA_DIR
from thunderhead.server.setup import run_setup
from thunderhead.server.tray import run_tray


def start_server(config: dict, no_ssl: bool = False) -> subprocess.Popen:
    port = config["port"]
    cert = os.path.join(DATA_DIR, "cert.pem")
    key = os.path.join(DATA_DIR, "key.pem")

    env = os.environ.copy()
    env["THUNDERHEAD_CONFIG"] = os.path.join(DATA_DIR, "config.json")

    use_ssl = not no_ssl and os.path.exists(cert) and os.path.exists(key)

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "thunderhead.server.app:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--log-level", "info",
    ]

    if use_ssl:
        cmd += ["--ssl-certfile", cert, "--ssl-keyfile", key]

    proc = subprocess.Popen(cmd, env=env)
    return proc, use_ssl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ssl", action="store_true", help="Run without HTTPS")
    args = parser.parse_args()

    config = load_config()
    if not config or not config.get("configured"):
        config = run_setup()

    proc, use_ssl = start_server(config, no_ssl=args.no_ssl)
    proto = "https" if use_ssl else "http"
    print(f"  Thunderhead running at {proto}://localhost:{config['port']}")
    print(f"  VPS Storage: {config['storage_root']}")
    print("  Check the system tray for controls")

    webbrowser.open(f"{proto}://localhost:{config['port']}")

    run_tray(config, proc, use_ssl=use_ssl)


if __name__ == "__main__":
    main()
