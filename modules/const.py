# modules/const.py — 安全なデフォルト内蔵 + TOML/ENV 上書き対応
from __future__ import annotations
import os
from pathlib import Path

# tomllib(3.11+)/tomli(3.10) 両対応
try:
    import tomllib  # type: ignore
except Exception:
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.toml"

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}

CONFIG: dict = _load_config()
SEL: dict = CONFIG.get("selectors", {}) or {}
APP: dict = CONFIG.get("app", {}) or {}
SLEEP: dict = CONFIG.get("sleep", {}) or {}

# ---- 既定セレクタ（ここだけで完結するよう一式定義） ----
DEFAULTS = {
    # URL
    "gin_menu_url": "https://yoyaku.city.nerima.tokyo.jp/stagia/reserve/gin_menu",

    # 入口・操作
    "multifunc": "img[alt='多機能操作'], input[alt='多機能操作'], a:has-text('多機能操作')",
    "left_avail_menu": "a:has-text('空き状況の確認')",
    "search_button": "input[type='submit'][value*='検索'], button:has-text('検索'), img[alt='検索']",
    "next_button": "a:has-text('次へ'), input[type='button'][value='次へ']",

    # 抽出（○セル）
    "ok_cell": "td.ok img[alt='O'], td.ok",

    # 例外画面の検出・復帰
    "error_text": "text=エラーが発生しました, text=一定時間操作がなかった場合, text=アクセス権限がありません",
    "error_buttons": "a:has-text('TOPへ'), input[value='確 定'], button:has-text('確定'), button:has-text('閉じる'), a:has-text('閉じる')",
}
ALIASES = {
    "multifunc": ("multifunc", "multifunc_button"),
    "left_avail_menu": ("left_avail_menu",),
    "search_button": ("search_button", "search"),
    "next_button": ("next_button", "next"),
    "ok_cell": ("ok_cell", "ok", "ok_selector"),
    "error_text": ("error_text", "error"),
    "error_buttons": ("error_buttons", "to_top", "close_button"),
    "gin_menu_url": ("gin_menu_url",),
}

def _get_sel(key: str) -> str:
    for k in ALIASES.get(key, (key,)):
        v = SEL.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return DEFAULTS[key]

# ---- 公開（他モジュールが import） ----
URL_GIN_MENU       = _get_sel("gin_menu_url")
MULTIFUNC_SELECTOR = _get_sel("multifunc")
LEFT_AVAIL_MENU    = _get_sel("left_avail_menu")
SEARCH_BUTTON      = _get_sel("search_button")
NEXT_BUTTON        = _get_sel("next_button")
OK_CELL_SELECTOR   = _get_sel("ok_cell")
ERROR_TEXT_SELECTOR    = _get_sel("error_text")
ERROR_BUTTONS_SELECTOR = _get_sel("error_buttons")

# ---- アプリ設定（未定義なら既定値）
USER_AGENT        = APP.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari")
STEP_TIMEOUT_SEC  = int(APP.get("step_timeout_sec", 40))
TOTAL_TIMEOUT_SEC = int(APP.get("total_timeout_sec", 300))

# ---- スリープ/リトライ設定（runner.py から import される）
# 初期待機（ページロード直後に少し待つ）
INITIAL_SLEEP_MS_MIN = int(os.getenv("INITIAL_SLEEP_MS_MIN", SLEEP.get("initial_min_ms", 150)))
INITIAL_SLEEP_MS_MAX = int(os.getenv("INITIAL_SLEEP_MS_MAX", SLEEP.get("initial_max_ms", 400)))

# ページング間の待機（仕様書：300–800ms のランダムスリープ）
PAGE_SLEEP_MS_MIN = int(os.getenv("PAGE_SLEEP_MS_MIN", SLEEP.get("page_min_ms", 300)))
PAGE_SLEEP_MS_MAX = int(os.getenv("PAGE_SLEEP_MS_MAX", SLEEP.get("page_max_ms", 800)))

# 重要操作のリトライ回数
RETRY_MAX = int(os.getenv("RETRY_MAX", SLEEP.get("retry_max", 3)))
