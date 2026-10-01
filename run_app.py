"""Launch the FastColis API, and the Vite frontend when it is available."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "app" / "frontend"


def main() -> None:
    frontend_process = None
    if (FRONTEND / "package.json").exists():
        npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
        frontend_process = subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=FRONTEND,
        )
        print("Frontend: http://127.0.0.1:5173")
    print("API:       http://127.0.0.1:8000/api/health")
    try:
        uvicorn.run(
            "app.backend.main:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
        )
    finally:
        if frontend_process is not None:
            frontend_process.terminate()


if __name__ == "__main__":
    main()
