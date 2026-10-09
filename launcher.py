"""Windows desktop entry point and headless release smoke test."""
import argparse
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn
from secureaudit_central import __version__
from secureaudit_central.api import create_app


def configure_source_tk():
    """Use optional matching Tcl libraries when the development runtime lacks them."""
    if not getattr(sys, "frozen", False):
        base = Path(__file__).parent / ".tools"
        for variable, folder in (("TCL_LIBRARY", "tcl-core-8-6-12"), ("TK_LIBRARY", "tk-core-8-6-12")):
            library = base / folder / "library"
            if library.is_dir():
                os.environ.setdefault(variable, str(library.resolve()))


def access_key(data_dir):
    path = data_dir / "access.key"
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if len(token) < 32:
            raise ValueError("Invalid access.key; restore the original key or remove it to generate a new one")
        return token
    token = secrets.token_hex(32)
    # Exclusive creation avoids overwriting a key during concurrent starts.
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(token)
    except FileExistsError:
        return access_key(data_dir)
    return token


def request(base_url, token, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base_url + path, data=data, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def release_self_test():
    import tkinter as tk
    from core.scanner import load_catalog, resolve_approved_script
    root = tk.Tk()
    root.withdraw()
    tk_version = root.tk.eval("info patchlevel")
    root.destroy()
    catalog = load_catalog()
    for check in catalog["checks"]:
        resolve_approved_script(check)
    with tempfile.TemporaryDirectory(prefix="secureaudit-smoke-") as folder:
        token = secrets.token_hex(32)
        app = create_app("sqlite:///" + (Path(folder) / "test.db").as_posix(), token)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False, log_config=None))
        thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 30
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("Packaged server did not start")
                time.sleep(0.1)
            health = request(base, token, "/health")
            seed = request(base, token, "/api/demo/seed", {"count": 10})
            endpoints = request(base, token, "/api/endpoints")
            jobs = request(base, token, "/api/demo/jobs", {"endpoint_ids": [e["id"] for e in endpoints]})
            while time.monotonic() < deadline:
                if all(j["status"] == "completed" for j in request(base, token, "/api/jobs")):
                    break
                time.sleep(0.2)
            summary = request(base, token, "/api/summary")
            evidence = request(base, token, "/api/export")
            assert summary["assessed_endpoints"] == 10, summary
            assert len(evidence["assessments"]) == 10
            for path in ("/", "/app.js", "/style.css"):
                with urllib.request.urlopen(base + path, timeout=10) as response:
                    assert response.status == 200 and len(response.read()) > 100
            result = {"self_test": "passed", "version": __version__, "health": health,
                      "tk_version": tk_version, "bundled_checks": len(catalog["checks"]),
                      "seeded": seed["created"], "jobs": jobs["count"], "summary": summary}
        finally:
            server.should_exit = True
            thread.join(timeout=15)
            sock.close()
            if thread.is_alive():
                raise RuntimeError("Packaged server failed to shut down")
        return result


def main():
    parser = argparse.ArgumentParser(description="SecureAudit Central M5 preview")
    parser.add_argument("--headless", action="store_true", help="Run the local API without a desktop window")
    parser.add_argument("--self-test", action="store_true", help="Exercise the packaged API, assets, queue and evidence export")
    parser.add_argument("--result-file", type=Path, help="Save self-test output as JSON (for a windowed executable)")
    parser.add_argument("--admin", action="store_true", help="Request UAC elevation before starting the desktop app")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SECUREAUDIT_PORT", "8765")))
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("SECUREAUDIT_DATA_DIR", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SecureAuditCentral"))))
    args = parser.parse_args()
    configure_source_tk()
    if args.self_test:
        result = release_self_test()
        if args.result_file:
            args.result_file.parent.mkdir(parents=True, exist_ok=True)
            args.result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        if sys.stdout is not None:
            print(json.dumps(result, indent=2))
        return
    if args.admin:
        from core.admin import request_elevation
        if request_elevation() != "already_elevated":
            return
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    args.data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=args.data_dir / "central.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    token = access_key(args.data_dir)
    database_url = os.environ.get("SECUREAUDIT_DATABASE_URL", "sqlite:///" + (args.data_dir / "central.db").as_posix())
    app = create_app(database_url, token)
    url = f"http://127.0.0.1:{args.port}"
    config = uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False, log_config=None)
    server = uvicorn.Server(config)
    if args.headless:
        print(f"SecureAudit Central {__version__}: {url}\nAccess key file: {args.data_dir / 'access.key'}", flush=True)
        server.run()
        return
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.title(f"SecureAudit Central {__version__}")
    root.geometry("540x370")
    root.resizable(False, False)
    root.configure(bg="#0b1020")
    def label(text, size=12, color="#9caac5"):
        tk.Label(root, text=text, font=("Segoe UI", size), fg=color, bg="#0b1020", wraplength=470).pack(pady=9)
    label("SecureAudit Central", 24, "#ffffff")
    label("M5 central evidence service · local desktop preview", 11)
    status = tk.StringVar(value="Starting local API…")
    tk.Label(root, textvariable=status, fg="#7adcb9", bg="#0b1020", font=("Segoe UI", 12)).pack(pady=10)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    opened = False
    deadline = time.monotonic() + 30
    def open_dashboard():
        webbrowser.open(url + "/#key=" + token)
    tk.Button(root, text="Open dashboard", command=open_dashboard, font=("Segoe UI", 12),
              bg="#4169ed", fg="white", relief="flat", padx=30, pady=10).pack(pady=10)
    label("Demo assessments are synthetic. 'Scan this PC' runs your approved checks.\nClose this window to stop the local server.", 10)
    def show_key():
        dialog = tk.Toplevel(root)
        dialog.title("Local API access key")
        tk.Label(dialog, text="Keep this key private. It grants access to local evidence.").pack(padx=20, pady=10)
        field = tk.Entry(dialog, width=76)
        field.insert(0, token)
        field.config(state="readonly")
        field.pack(padx=20, pady=10)
    tk.Button(root, text="View access key", command=show_key).pack()
    def check():
        nonlocal opened
        if server.started:
            status.set("Local API ready · " + url)
            if not opened:
                open_dashboard()
                opened = True
        elif not thread.is_alive() or time.monotonic() > deadline:
            server.should_exit = True
            status.set("Unable to start server")
            messagebox.showerror("SecureAudit startup", "The server could not start. Check whether port 8765 is in use and inspect central.log in the data folder.")
            return
        root.after(500, check)
    def close():
        server.should_exit = True
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, check)
    root.mainloop()
    thread.join(timeout=10)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if "--headless" in sys.argv or "--self-test" in sys.argv:
            raise
        import tkinter.messagebox
        tkinter.messagebox.showerror("SecureAudit Central", f"Startup failed ({type(exc).__name__}). Check the data directory and database configuration.")
        sys.exit(1)
