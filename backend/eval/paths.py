"""paths.py – Shared path resolution for evaluation and metrics."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def get_eval_dir() -> Path:
    """Return absolute path to backend/eval directory."""
    return Path(__file__).resolve().parent


def get_metrics_dir() -> Path:
    """Resolve and validate metrics directory path according to rules:
    1. If the environment variable METRICS_DIR is set, use it.
    2. Else if running inside Docker (Path('/.dockerenv') exists), use /app/metrics.
       Confirm it is a real bind mount by reading /proc/self/mountinfo. If it is
       not a mount, print 'ERROR: /app/metrics is not mounted; check docker-compose.yml'
       and exit 1.
    3. Else (running on the host), walk up from this file's location until you find
       a folder containing docker-compose.yml and use its metrics/ subfolder.

    Rules:
    - Never use the current working directory.
    - Never create the metrics folder (if it does not exist, print an error and exit 1).
    """
    metrics_path: Path | None = None

    # 1. Environment variable METRICS_DIR
    env_metrics = os.environ.get("METRICS_DIR")
    if env_metrics:
        metrics_path = Path(env_metrics).resolve()

    # 2. Inside Docker
    elif Path("/.dockerenv").exists():
        target_mount = "/app/metrics"
        mountinfo = Path("/proc/self/mountinfo")
        is_mounted = False
        if mountinfo.is_file():
            try:
                with open(mountinfo, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5 and parts[4].rstrip("/") == target_mount:
                            is_mounted = True
                            break
            except Exception as e:
                print(f"ERROR: Failed to read /proc/self/mountinfo: {e}", file=sys.stderr)
                sys.exit(1)

        if not is_mounted:
            print("ERROR: /app/metrics is not mounted; check docker-compose.yml", file=sys.stderr)
            sys.exit(1)

        metrics_path = Path(target_mount).resolve()

    # 3. Running on the host
    else:
        curr = Path(__file__).resolve().parent
        repo_root: Path | None = None
        for parent in [curr, *curr.parents]:
            if (parent / "docker-compose.yml").is_file():
                repo_root = parent
                break

        if repo_root is None:
            print("ERROR: docker-compose.yml not found while searching up from paths.py", file=sys.stderr)
            sys.exit(1)

        metrics_path = (repo_root / "metrics").resolve()

    # Common validation: never create, must exist and be a directory
    if not metrics_path.is_dir():
        print(f"ERROR: Metrics directory '{metrics_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    return metrics_path

