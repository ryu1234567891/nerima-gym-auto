# modules/const.py — 落ちない既定値＋互換エイリアス完備版
from __future__ import annotations
import os
from pathlib import Path

# tomllib(3.11+) / tomli(3.10) 両対応
try:
    import tomllib  # type: ignore
except Exception:
    import tomli as tomllib  # type: ignore

# ---------- 設定読込 ----------
ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.toml"

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}

CFG: dict = _load_config()
SEL: dict = (CFG.get("selectors") or {})
APP: dict = (CFG.get("app") or {})
SLEEP: dict = (CFG.get("sleep") or {})

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

# ---------- 既定セレクタ & URL ----------
_DEFAULT_SELECTORS = {
    "gin_menu_url": "https://yoyaku.city.nerima.tokyo.jp/stagia/reserve/gin_menu",
    "multifunc": "img[alt='多機能操作'], input[alt='多機能操作'], a:has-text('多機能操作')",
    "left_avail_menu": "a:has-text('空き状況の確認')",
    "search_button": "input[type='submit'][value*='検索'], button:has-text('検索'), img[alt='検索']",
    "next_button": "a:has-text('次へ'), input[type='button'][value='次へ']",
    "ok_cell": "td.ok img[alt='O'], td.ok",
    "error_text": "text=エラーが発生しました, text=一定時間操作がなかった場合, text=アクセス権限がありません",
    "error_buttons": "a:has-text('TOPへ'), input[value='確 定'], button:has-text('確定'), button:has-text('閉じる'), a:has-text('閉じる')",
}

# 旧名の互換
_ALIAS = {
    "multifunc": ("multifunc", "multifunc_button"),
    "left_avail_menu": ("left_avail_menu",),
    "search_button": ("search_button", "search"),
    "next_button": ("next_button", "next"),
    "ok_cell": ("ok_cell", "ok", "ok_selector"),
    "error_text": ("error_text", "error"),
    "error_buttons": ("error_buttons", "to_top", "close_button"),
    "gin_menu_url": ("gin_menu_url",),
}

def _sel(key: str) -> str:
    for k in _ALIAS.get(key, (key,)):
        v = SEL.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return _DEFAULT_SELECTORS[key]

# 公開：URL/セレクタ
URL_GIN_MENU            = _sel("gin_menu_url")
MULTIFUNC_SELECTOR      = _sel("multifunc")
LEFT_AVAIL_MENU         = _sel("left_avail_menu")
SEARCH_BUTTON           = _sel("search_button")
NEXT_BUTTON             = _sel("next_button")
OK_CELL_SELECTOR        = _sel("ok_cell")
ERROR_TEXT_SELECTOR     = _sel("error_text")
ERROR_BUTTONS_SELECTOR  = _sel("error_buttons")

# ---------- タイムアウト ----------
USER_AGENT        = APP.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari")
STEP_TIMEOUT_SEC  = int(APP.get("step_timeout_sec", 40))
TOTAL_TIMEOUT_SEC = int(APP.get("total_timeout_sec", 300))

# ---------- 待機・リトライ（ENV / config.toml / 既定 の順で採用） ----------
# 初期のちょい待ち
INITIAL_SLEEP_MS_MIN = _env_int("INITIAL_SLEEP_MS_MIN", int(SLEEP.get("initial_min_ms", 150)))
INITIAL_SLEEP_MS_MAX = _env_int("INITIAL_SLEEP_MS_MAX", int(SLEEP.get("initial_max_ms", 400)))
# ページング間（仕様：300–800ms）
PAGE_SLEEP_MS_MIN     = _env_int("PAGE_SLEEP_MS_MIN", int(SLEEP.get("page_min_ms", 300)))
PAGE_SLEEP_MS_MAX     = _env_int("PAGE_SLEEP_MS_MAX", int(SLEEP.get("page_max_ms", 800)))
# リトライ回数
RETRY_MAX             = _env_int("RETRY_MAX", int(SLEEP.get("retry_max", 3)))

# ---------- 互換エイリアス（runner.py が古い名前で import しても落ちない） ----------
# 旧コードが import しても動くように別名を公開
MAX_RETRIES            = RETRY_MAX
CLICK_RETRY_MAX        = RETRY_MAX  # 慣用的に使われがち
PAGING_SLEEP_MS_MIN    = PAGE_SLEEP_MS_MIN
PAGING_SLEEP_MS_MAX    = PAGE_SLEEP_MS_MAX

# ==== compatibility aliases (do not remove) ====
# URL 名称ゆれ
GIN_MENU_URL = URL_GIN_MENU

# セレクタ: *_SELECTOR で import しても動くように
MULTIFUNC_BTN_SELECTOR     = MULTIFUNC_SELECTOR
LEFT_AVAIL_MENU_SELECTOR   = LEFT_AVAIL_MENU
SEARCH_BTN_SELECTOR        = SEARCH_BUTTON
NEXT_BTN_SELECTOR          = NEXT_BUTTON
OK_SELECTOR                = OK_CELL_SELECTOR
ERROR_BTN_SELECTOR         = ERROR_BUTTONS_SELECTOR

# リトライ／スリープ名称ゆれ
MAX_RETRIES         = RETRY_MAX
CLICK_RETRY_MAX     = RETRY_MAX
PAGING_SLEEP_MS_MIN = PAGE_SLEEP_MS_MIN
PAGING_SLEEP_MS_MAX = PAGE_SLEEP_MS_MAX
