# modules/const.py — 安全既定＋TOML/ENV上書き＋互換エイリアスてんこ盛り
from __future__ import annotations
import os
from pathlib import Path

# tomllib(3.11+)/tomli(3.10) 両対応
try:
    import tomllib  # type: ignore[attr-defined]
except Exception:
    import tomli as tomllib  # type: ignore[assignment]

# ----------------------------
# 設定ファイル読込
# ----------------------------
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

# ----------------------------
# セレクタ既定値
# ----------------------------
_DEFAULT_SELECTORS = {
    # URL
    "gin_menu_url": "https://yoyaku.city.nerima.tokyo.jp/stagia/reserve/gin_menu",

    # 入口・操作
    "multifunc": "img[alt='多機能操作'], input[alt='多機能操作'], a:has-text('多機能操作')",
    "left_avail_menu": "a:has-text('空き状況の確認')",
    "search_button": "input[type='submit'][value*='検索'], button:has-text('検索'), img[alt='検索']",
    "next_button": "a:has-text('次へ'), input[type='button'][value='次へ']",

    # 抽出（○セル）
    "ok_cell": "td.ok img[alt='O'], td.ok",

    # エラー検出（本文テキスト）
    "error_text": "text=エラーが発生しました, text=一定時間操作がなかった場合, text=アクセス権限がありません",
    # 代表ボタン一括
    "error_buttons": "a:has-text('TOPへ'), input[value='確 定'], button:has-text('確定'), button:has-text('閉じる'), a:has-text('閉じる')",
}

# 旧キー名の互換
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
    """TOML > 既定値 の順でセレクタ文字列を返す。旧名も吸収。"""
    for k in _ALIAS.get(key, (key,)):
        v = SEL.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return _DEFAULT_SELECTORS[key]

# ----------------------------
# 公開：URL/セレクタ（本名）
# ----------------------------
URL_GIN_MENU            = _sel("gin_menu_url")
MULTIFUNC_SELECTOR      = _sel("multifunc")
LEFT_AVAIL_MENU         = _sel("left_avail_menu")
SEARCH_BUTTON           = _sel("search_button")
NEXT_BUTTON             = _sel("next_button")
OK_CELL_SELECTOR        = _sel("ok_cell")

# エラー本文（まとめ）
ERROR_TEXT_SELECTOR     = _sel("error_text")
# よく使う個別テキスト（名称ゆれ対策で個別にも用意）
GENERIC_ERROR_SELECTOR  = "text=エラーが発生しました"
TIMEOUT_SELECTOR        = "text=一定時間操作がなかった場合"
ACCESS_DENIED_SELECTOR  = "text=アクセス権限がありません"

# エラーボタン群（まとめ）
ERROR_BUTTONS_SELECTOR  = _sel("error_buttons")

# 個別ボタン（確定/TOP/閉じる）— 旧コードが単体名で呼んでも耐えるよう明示
CONFIRM_BUTTON = "input[value='確 定'], button:has-text('確定')"
TOP_BUTTON     = "a:has-text('TOPへ')"
CLOSE_BUTTON   = "button:has-text('閉じる'), a:has-text('閉じる')"

# ----------------------------
# タイムアウト等（本名）
# ----------------------------
USER_AGENT        = APP.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari")
STEP_TIMEOUT_SEC  = int(APP.get("step_timeout_sec", 40))
TOTAL_TIMEOUT_SEC = int(APP.get("total_timeout_sec", 300))

# ----------------------------
# スリープ／リトライ（ENV → TOML → 既定 の順）
# ----------------------------
# 初期待機（ページロード直後に少し待つ）
INITIAL_SLEEP_MS_MIN = _env_int("INITIAL_SLEEP_MS_MIN", int(SLEEP.get("initial_min_ms", 150)))
INITIAL_SLEEP_MS_MAX = _env_int("INITIAL_SLEEP_MS_MAX", int(SLEEP.get("initial_max_ms", 400)))
# ページング間（仕様：300–800ms）
PAGE_SLEEP_MS_MIN     = _env_int("PAGE_SLEEP_MS_MIN", int(SLEEP.get("page_min_ms", 300)))
PAGE_SLEEP_MS_MAX     = _env_int("PAGE_SLEEP_MS_MAX", int(SLEEP.get("page_max_ms", 800)))
# リトライ回数
RETRY_MAX             = _env_int("RETRY_MAX", int(SLEEP.get("retry_max", 3)))

# ----------------------------
# 互換エイリアスを一括エクスポート
# （古い/別名 import でも落ちないように吸収）
# ----------------------------
GIN_MENU_URL = URL_GIN_MENU  # URL 名称ゆれ

_compat_map = {
    # 入口・操作（*_SELECTOR 名で import されてもOK）
    "MULTIFUNC_BTN_SELECTOR":    MULTIFUNC_SELECTOR,
    "LEFT_AVAIL_MENU_SELECTOR":  LEFT_AVAIL_MENU,
    "SEARCH_BTN_SELECTOR":       SEARCH_BUTTON,
    "NEXT_BTN_SELECTOR":         NEXT_BUTTON,

    # 抽出
    "OK_SELECTOR":               OK_CELL_SELECTOR,
    "OK_CELL":                   OK_CELL_SELECTOR,

    # エラー本文（個別も含む）
    "ERROR_TEXTS":               ERROR_TEXT_SELECTOR,
    "ERROR_TEXT":                ERROR_TEXT_SELECTOR,
    "GENERIC_ERROR_SELECTOR":    GENERIC_ERROR_SELECTOR,
    "TIMEOUT_TEXT_SELECTOR":     TIMEOUT_SELECTOR,
    "TIMEOUT_SELECTOR":          TIMEOUT_SELECTOR,
    "ACCESS_DENIED_SELECTOR":    ACCESS_DENIED_SELECTOR,
    "ACCESS_DENIED_TEXT":        ACCESS_DENIED_SELECTOR,
    "ERROR_PAGE_TEXT":           GENERIC_ERROR_SELECTOR,

    # エラーボタン群／個別ボタン
    "ERROR_BTN_SELECTOR":        ERROR_BUTTONS_SELECTOR,
    "CONFIRM_BTN_SELECTOR":      CONFIRM_BUTTON,
    "CONFIRM_SELECTOR":          CONFIRM_BUTTON,
    "TO_TOP_BTN_SELECTOR":       TOP_BUTTON,
    "TOP_SELECTOR":              TOP_BUTTON,
    "CLOSE_BTN_SELECTOR":        CLOSE_BUTTON,
    "CLOSE_SELECTOR":            CLOSE_BUTTON,
    "POPUP_CLOSE_SELECTOR":      CLOSE_BUTTON,

    # リトライ/スリープ名称ゆれ
    "MAX_RETRIES":               RETRY_MAX,
    "CLICK_RETRY_MAX":           RETRY_MAX,
    "PAGING_SLEEP_MS_MIN":       PAGE_SLEEP_MS_MIN,
    "PAGING_SLEEP_MS_MAX":       PAGE_SLEEP_MS_MAX,
}

globals().update(_compat_map)
