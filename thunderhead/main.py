import argparse
import os
import socket

import uvicorn

from thunderhead.config import load_config, DATA_DIR
from thunderhead.server.setup import run_setup


def get_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ssl", action="store_true", help="Run without HTTPS")
    args = parser.parse_args()

    config = load_config()
    if not config or not config.get("configured"):
        config = run_setup()

    port = config["port"]
    cert = os.path.join(DATA_DIR, "cert.pem")
    key = os.path.join(DATA_DIR, "key.pem")
    use_ssl = not args.no_ssl and os.path.exists(cert) and os.path.exists(key)

    os.environ["THUNDERHEAD_CONFIG"] = os.path.join(DATA_DIR, "config.json")

    ip = get_ip()
    proto = "https" if use_ssl else "http"
    print(f"[Thunderhead] running on {proto}://{ip}:{port}")
    print(f"[Thunderhead] storage: {config['storage_root']}")
    print(f"[Thunderhead] press Ctrl+C to stop")

    ssl_kwargs = {"ssl_certfile": cert, "ssl_keyfile": key} if use_ssl else {}
    uvicorn.run(
        "thunderhead.server.app:app",
        host="0.0.0.0",
        port=port,
        log_level="warning",
        access_log=False,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
