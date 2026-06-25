import asyncio
import os
import time
from pathlib import Path

from thunderhead.client.api import ThunderheadClient


def format_size(bytes: int) -> str:
    if bytes == 0:
        return "-"
    units = ["B", "KB", "MB", "GB"]
    i = min(int(bytes.bit_length() / 10), len(units) - 1)
    return f"{bytes / (1024 ** i):.1f} {units[i]}" if i > 0 else f"{bytes} B"


def format_date(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


async def run():
    address = input("Server address [localhost:8443]: ").strip() or "localhost:8443"
    password = input("Password: ").strip()
    if not password:
        print("Password required")
        return

    client = ThunderheadClient(address, password)
    print("Connecting...")
    try:
        ok = await client.login()
    except Exception:
        ok = False
    if not ok:
        print("Connection failed")
        return

    current_path = "/"
    print("Connected. Type 'help' for commands.")

    while True:
        try:
            line = input(f"thunderhead {current_path}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("q", "quit", "exit"):
            break

        elif cmd == "help":
            print("  ls                    List files")
            print("  cd <path>             Change directory")
            print("  get <file>            Download file")
            print("  put <local_path>      Upload file")
            print("  mkdir <name>          Create folder")
            print("  rm <name>             Delete file/folder")
            print("  pwd                   Show current path")
            print("  q/quit/exit           Disconnect")

        elif cmd == "pwd":
            print(current_path)

        elif cmd == "ls":
            items = await client.list_files(current_path)
            if items is None:
                print("Failed to list files")
                continue
            if not items:
                print("(empty)")
            else:
                for item in items:
                    icon = "d" if item["is_dir"] else " "
                    size = "-" if item["is_dir"] else format_size(item["size"])
                    date = format_date(item["modified"])
                    print(f"  [{icon}] {item['name']:<30} {size:>8}  {date}")

        elif cmd == "cd":
            if not arg or arg == "~":
                current_path = "/"
            elif arg == "..":
                current_path = current_path.rstrip("/").rsplit("/", 1)[0] or "/"
            elif arg.startswith("/"):
                current_path = arg
            else:
                current_path = current_path.rstrip("/") + "/" + arg

        elif cmd == "get":
            if not arg:
                print("Usage: get <filename>")
                continue
            path = current_path.rstrip("/") + "/" + arg
            data = await client.download(path)
            if data:
                Path(arg).write_bytes(data)
                print(f"Downloaded {arg} ({len(data)} bytes)")
            else:
                print("Download failed")

        elif cmd == "put":
            if not arg:
                print("Usage: put <local_path>")
                continue
            p = Path(arg)
            if not p.is_file():
                print(f"File not found: {arg}")
                continue
            content = p.read_bytes()
            ok = await client.upload(current_path, p.name, content)
            print("Uploaded" if ok else "Upload failed")

        elif cmd == "mkdir":
            if not arg:
                print("Usage: mkdir <name>")
                continue
            path = current_path.rstrip("/") + "/" + arg
            ok = await client.mkdir(path)
            print("Created" if ok else "Failed")

        elif cmd == "rm":
            if not arg:
                print("Usage: rm <name>")
                continue
            path = current_path.rstrip("/") + "/" + arg
            ok = await client.remove(path)
            print("Removed" if ok else "Failed")

        else:
            print(f"Unknown command: {cmd}")

    await client.close()


def run_client():
    asyncio.run(run())
