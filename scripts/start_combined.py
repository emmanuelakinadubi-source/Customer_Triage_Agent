from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def start_process(command: list[str], name: str) -> subprocess.Popen:
    print(f"Starting {name}: {' '.join(command)}", flush=True)
    return subprocess.Popen(command, cwd="/app")


def main() -> int:
    os.environ.setdefault("API_URL", "http://127.0.0.1:8000")

    processes = [
        start_process(
            ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            "FastAPI",
        ),
        start_process(
            [
                "streamlit",
                "run",
                "ui/app.py",
                "--server.address=0.0.0.0",
                "--server.port=8501",
                "--server.headless=true",
            ],
            "Streamlit",
        ),
    ]

    stopping = False

    def stop_all(signum: int, _frame) -> None:
        nonlocal stopping
        stopping = True
        print(f"Received signal {signum}; stopping services.", flush=True)
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop_all)
    signal.signal(signal.SIGINT, stop_all)

    while not stopping:
        for process in processes:
            code = process.poll()
            if code is not None:
                print(f"Process exited with code {code}; stopping container.", flush=True)
                for other in processes:
                    if other.poll() is None:
                        other.terminate()
                return code
        time.sleep(1)

    deadline = time.time() + 10
    while time.time() < deadline:
        if all(process.poll() is not None for process in processes):
            return 0
        time.sleep(0.5)

    for process in processes:
        if process.poll() is None:
            process.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
