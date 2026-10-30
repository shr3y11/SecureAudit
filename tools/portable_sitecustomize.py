"""Supported embedded-Python startup for the portable desktop distribution.

Only the renamed windowed interpreter opens the app. The original python.exe
remains a normal interpreter for diagnostics. Its vendor signature is unchanged.
"""
import json
import os
from pathlib import Path
import sys

if Path(sys.executable).stem.lower() == "secureauditcentral":
    package = Path(sys.executable).resolve().parent
    os.environ["TCL_LIBRARY"] = str(package / "_tcl_data")
    os.environ["TK_LIBRARY"] = str(package / "_tk_data")
    sys.frozen = True
    sys._MEIPASS = str(package / "app")
    sys.argv = [str(package / "app" / "launcher.py")]
    if os.environ.get("SECUREAUDIT_HEADLESS") == "1":
        sys.argv.append("--headless")
    from launcher import main, release_self_test
    try:
        if os.environ.get("SECUREAUDIT_SELF_TEST_RESULT"):
            result = release_self_test()
            Path(os.environ["SECUREAUDIT_SELF_TEST_RESULT"]).write_text(json.dumps(result, indent=2), encoding="utf-8")
        else:
            # Keep this cwd independent: resources and writable paths are absolute.
            main()
    except Exception as exc:
        if os.environ.get("SECUREAUDIT_SELF_TEST_RESULT"):
            Path(os.environ["SECUREAUDIT_SELF_TEST_RESULT"]).write_text(json.dumps({"self_test": "failed", "error": type(exc).__name__, "message": str(exc)}), encoding="utf-8")
        else:
            from tkinter import messagebox
            messagebox.showerror("SecureAudit Central", f"Startup failed ({type(exc).__name__}). Check database configuration and runtime data permissions.")
        # os._exit is necessary here: SystemExit during site initialization is
        # treated by CPython as a fatal interpreter startup error.
        os._exit(1)
    os._exit(0)
