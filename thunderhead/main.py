import argparse
import os
import sys

import uvicorn

from thunderhead.config import load_config, DATA_DIR
from thunderhead.server.setup import run_setup


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

    proto = "https" if use_ssl else "http"
    print(f"Thunderhead running at {proto}://0.0.0.0:{port}")
    print(f"Storage: {config['storage_root']}")
    print("---")

    ssl_kwargs = {"ssl_certfile": cert, "ssl_keyfile": key} if use_ssl else {}
    uvicorn.run(
        "thunderhead.server.app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
