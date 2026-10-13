"""Collect reproducible, real CLI outputs for the OS2026 submission.

Run with: conda run -n pulse python scripts/competition/collect_evidence.py
"""

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "os2026"
OUT.mkdir(parents=True, exist_ok=True)

commands = [
    ("version", [sys.executable, "-m", "pulse.experiment", "--version"],
     "conda run -n pulse pulse-explore --version"),
    ("mechanism", [sys.executable, "-m", "pulse.experiment", "--output", "output/os2026/mechanism"],
     "conda run -n pulse pulse-explore --output output/os2026/mechanism"),
    ("city", [sys.executable, "scripts/run_city_demo.py", "--output", "output/os2026/city"],
     "conda run -n pulse python scripts/run_city_demo.py --output output/os2026/city"),
    ("ai_guard", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_city.py", "-v"],
     "conda run -n pulse python -m unittest discover -s tests -p test_city.py -v"),
    ("verify", [sys.executable, "scripts/verify_evidence_chain.py"],
     "conda run -n pulse python scripts/verify_evidence_chain.py"),
]
records = []
for name, argv, display in commands:
    started = time.monotonic()
    proc = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = proc.stdout.replace(str(ROOT), "<PROJECT>")
    record = dict(name=name, command=display, exit_code=proc.returncode,
                  wall_seconds=round(time.monotonic()-started, 3), output=output)
    records.append(record)
    (OUT / f"{name}.txt").write_text(f"$ {display}\n\n{output}", encoding="utf-8")
    print(name, "exit", proc.returncode, "seconds", record["wall_seconds"], flush=True)
    if proc.returncode:
        raise SystemExit(proc.stdout)

manifest = {
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "recorded_date": "2026-10-13", "timezone": "Asia/Shanghai",
    "python": platform.python_version(), "platform": platform.platform(),
    "commands": records,
    "files": {},
}
for folder in [OUT / "mechanism", OUT / "city"]:
    for path in sorted(folder.glob("*")):
        if path.is_file():
            manifest["files"][str(path.relative_to(OUT))] = hashlib.sha256(path.read_bytes()).hexdigest()
(OUT / "evidence.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("Evidence saved to output/os2026/evidence.json")
