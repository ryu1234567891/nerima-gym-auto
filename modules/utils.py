import re, unicodedata, hashlib, json
from datetime import datetime
from dataclasses import dataclass, asdict

WAVE_CHARS = r"[–—―〜～-]"

def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")

def squeeze_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def norm_text(s: str) -> str:
    return squeeze_ws(nfkc(s))

def to_iso_from_jp_era(s: str) -> str:
    # 想定入力例: "令和07年09月23日" or "令和7年9月23日"
    s = nfkc(s)
    m = re.search(r"(令和|平成)(\d+)年(\d{1,2})月(\d{1,2})日", s)
    if not m:
        # バックアップ：YYYY/MM/DD などを拾う
        m2 = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
        if m2:
            y, mo, d = map(int, m2.groups())
            return f"{y:04d}-{mo:02d}-{d:02d}"
        raise ValueError(f"Unsupported date format: {s}")
    era, y, mo, d = m.groups()
    y = int(y); mo = int(mo); d = int(d)
    base = 2018 if era == "令和" else 1988  # 平成=1989, 令和=2019
    year = base + y
    return f"{year:04d}-{mo:02d}-{d:02d}"

def extract_times(s: str):
    t = nfkc(s)
    t = re.sub(r"\s+", "", t)             # 改行/空白を除去
    t = re.sub(WAVE_CHARS, "～", t)        # ダッシュ類を統一
    m = re.search(r"(\d{1,2}:\d{2})～(\d{1,2}:\d{2})", t)
    return m.groups() if m else (None, None)

def facility_id(name: str) -> str:
    return "hash:" + hashlib.md5(norm_text(name).encode("utf-8")).hexdigest()[:8]

@dataclass(frozen=True)
class SlotKey:
    date_iso: str
    start: str
    end: str
    facility_id: str

def record_to_key(rec: dict) -> SlotKey:
    return SlotKey(rec["date_iso"], rec["start"], rec["end"], rec["facility_id"])

def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
