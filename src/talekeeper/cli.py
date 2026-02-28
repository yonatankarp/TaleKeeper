"""CLI entry point for TaleKeeper."""

import argparse
import sys
import webbrowser
from pathlib import Path

DATA_DIR = Path("data")
AUDIO_DIR = DATA_DIR / "audio"
DB_DIR = DATA_DIR / "db"


def ensure_data_dirs() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    DB_DIR.mkdir(parents=True, exist_ok=True)


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    ensure_data_dirs()

    host = args.host
    port = args.port

    if not args.no_browser:
        webbrowser.open(f"http://{host}:{port}")

    uvicorn.run(
        "talekeeper.app:app",
        host=host,
        port=port,
        reload=args.reload,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="talekeeper",
        description="TaleKeeper — Record, transcribe, and summarize D&D sessions",
    )
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start the TaleKeeper server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    serve.add_argument("--no-browser", action="store_true", help="Don't open browser on startup")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "serve":
        cmd_serve(args)
