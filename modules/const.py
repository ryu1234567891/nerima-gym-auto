# modules/const.py
from pathlib import Path
import os

# Python 3.11 未満でも動くよう tomllib/tomli フォールバック
try:
    import tomllib  # 3.11+
except ModuleNotFoundError:  # 3.10 など
    import tomli as tomllib  # type: ignore

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"
with open(CONFIG_PATH, "rb") as f:
    CONFIG = tomllib.load(f)

# ---- URLs ----
URL_GIN_MENU = CONFIG["selectors"]["gin_menu_url"]

# ---- selectors（強化版）----
MULTIFUNC_SELECTOR = CONFIG["selectors"]["multifunc"]

# 検索ボタンは input type=image(id=btnOK) を最優先で拾う
SEARCH_BTN_SELECTOR = (
    "input[type='image'][alt='検索'], "
    "#btnOK, "
    "input[type='submit'][value*='検索'], "
    "button:has-text('検索'), "
    "img[alt='検索']"
)

# 日付ナビの「次へ」だけを狙う（結果表の右上ナビにある a タグ）
NEXT_BTN_SELECTOR = (
    "ul.double.time-navigation li.right a:has-text('次へ'), "
    "a[href^='javaScript:changeDspDay']:has-text('次へ')"
)

OK_CELL_SELECTOR = CONFIG["selectors"]["ok_cell"]

# 「確定」/「確定・全検索」は表記・種類が揺れるため網羅的に
CONFIRM_BTN_SELECTOR = (
    "button:has-text('確定・全検索'), "
    "input[type='submit'][value*='確定・全検索'], "
    "input[type='button'][value*='確定・全検索'], "
    "button:has-text('確定'), "
    "input[type='submit'][value*='確定'], "
    "input[type='button'][value*='確定'], "
    "img[alt='確定']"
)

ERROR_TEXT_SELECTOR = CONFIG["selectors"]["error_text"]
ACCESS_DENIED_SELECTOR = CONFIG["selectors"]["access_denied_text"]
TOP_LINK_SELECTOR = CONFIG["selectors"]["top_link"]

# 左メニューの「空き状況の確認」リンク（/gml_init で使用）
LEFT_AVAIL_MENU = "a[href*='gml_z_group_sel_1'], a:has-text('空き状況の確認')"

# ---- HTTP / runtime ----
USER_AGENT = CONFIG["http"]["user_agent"]
INITIAL_SLEEP_MS_MIN = CONFIG["http"]["initial_sleep_ms_min"]
INITIAL_SLEEP_MS_MAX = CONFIG["http"]["initial_sleep_ms_max"]
PAGING_SLEEP_MS_MIN = CONFIG["http"]["paging_sleep_ms_min"]
PAGING_SLEEP_MS_MAX = CONFIG["http"]["paging_sleep_ms_max"]
STEP_TIMEOUT_SEC = CONFIG["http"]["step_timeout_sec"]
TOTAL_TIMEOUT_SEC = CONFIG["http"]["total_timeout_sec"]
MAX_RETRIES = CONFIG["http"]["max_retries"]

# ---- user-configurable labels（環境変数で上書き可）----
CATEGORY1_LABEL = os.getenv("CATEGORY1_LABEL", "屋内スポーツ施設")
PURPOSE_LABEL   = os.getenv("PURPOSE_LABEL",   "バレーボール")
