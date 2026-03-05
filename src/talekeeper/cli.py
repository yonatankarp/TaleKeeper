"""CLI entry point for TaleKeeper."""

import argparse
import sys
import webbrowser

from talekeeper.paths import get_db_dir, get_audio_dir


def ensure_data_dirs() -> None:
    get_audio_dir().mkdir(parents=True, exist_ok=True)
    get_db_dir().mkdir(parents=True, exist_ok=True)


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    ensure_data_dirs()

    host = args.host
    port = args.port
    open_browser = not args.no_browser

    class _Config(uvicorn.Config):
        pass

    log_config = uvicorn.config.LOGGING_CONFIG
    log_fmt = "%(asctime)s %(levelname)s:%(name)s: %(message)s"
    date_fmt = "%H:%M:%S"
    for formatter in log_config["formatters"].values():
        formatter["fmt"] = log_fmt
        formatter["datefmt"] = date_fmt

    server = uvicorn.Server(_Config(
        "talekeeper.app:app",
        host=host,
        port=port,
        reload=args.reload,
        log_config=log_config,
    ))

    original_startup = server.startup

    async def _startup_then_open(*a: object, **kw: object) -> None:
        await original_startup(*a, **kw)  # type: ignore[arg-type]
        if open_browser and server.started:
            webbrowser.open(f"http://{host}:{port}")

    server.startup = _startup_then_open  # type: ignore[assignment]
    server.run()


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
