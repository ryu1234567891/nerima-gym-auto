# modules/diffstore.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple

Record = Dict[str, str]  # {"date": "...", "time": "...", "facility": "..."}

class DiffStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.prev: List[Record] = []
        if self.path.exists():
            try:
                self.prev = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.prev = []

    @staticmethod
    def _key(r: Record) -> Tuple[str, str, str]:
        # 差分判定キー（ISO日付で扱っている前提）
        return (r.get("date", ""), r.get("time", ""), r.get("facility", ""))

    def diff(self, current: List[Record]) -> List[Record]:
        prev_keys = {self._key(r) for r in self.prev}
        return [r for r in current if self._key(r) not in prev_keys]

    def save(self, current: List[Record], mode: str = "union"):
        """
        mode="overwrite": currentで完全上書き（従来仕様）
        mode="union"    : 既存prevとcurrentの和集合で保存（カテゴリ横断に有効）
        """
        if mode == "overwrite":
            out = current
        else:
            # union（キーで重複排除）
            merged = {self._key(r): r for r in self.prev}
            for r in current:
                merged[self._key(r)] = r
            out = list(merged.values())

        self.path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        self.prev = out  # メモリも更新
