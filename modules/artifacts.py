from pathlib import Path
from datetime import datetime

def run_dir(base: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    d = base / f"run-{ts}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
