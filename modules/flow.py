# modules/flow.py
from pathlib import Path
import random
import time
from playwright.sync_api import Page

from .const import (
    URL_GIN_MENU,
    MULTIFUNC_SELECTOR,
    SEARCH_BTN_SELECTOR,
    NEXT_BTN_SELECTOR,
    OK_CELL_SELECTOR,           # 将来用に残す
    CONFIRM_BTN_SELECTOR,
    ACCESS_DENIED_SELECTOR,     # ガード用（今は未使用）
    USER_AGENT,                 # 将来のUA変更用（今は未使用）
    INITIAL_SLEEP_MS_MIN,
    INITIAL_SLEEP_MS_MAX,
    PAGING_SLEEP_MS_MIN,
    PAGING_SLEEP_MS_MAX,
    STEP_TIMEOUT_SEC,
    LEFT_AVAIL_MENU,            # go_to_availability_menu で使用
    CATEGORY1_LABEL,            # 環境変数で切り替え可（例：文化施設）
    PURPOSE_LABEL,              # 〃（例：合唱）
)
from .artifacts import save_text


# ===== helpers =====
def sleep_rand(ms_min: int, ms_max: int):
    time.sleep(random.uniform(ms_min / 1000, ms_max / 1000))


# ===== navigation primitives =====
def goto_menu(page: Page):
    """開始URLへダイレクト遷移。"""
    page.goto(URL_GIN_MENU, wait_until="domcontentloaded")


def click_multifunc(page: Page):
    """
    1枚目 /stagia/reserve/gin_menu にいるときだけ『多機能操作』を押す。
    /gml_init 以降では押さない（ボタンは出ない）。
    """
    url = page.url or ""
    if "gin_menu" not in url:
        return  # 2枚目以降は何もしない

    candidates = [
        "a:has(img[alt='多機能操作'])",
        "input[type='image'][alt='多機能操作']",
        "img[alt='多機能操作']",
        "button:has-text('多機能操作')",
        "a:has-text('多機能操作')",
    ]
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=500):
                loc.click(timeout=STEP_TIMEOUT_SEC * 1000)
                page.wait_for_load_state("domcontentloaded")
                return
        except Exception:
            pass

    # フォールバック（従来セレクタ）
    page.locator(MULTIFUNC_SELECTOR).first.click(timeout=STEP_TIMEOUT_SEC * 1000)
    page.wait_for_load_state("domcontentloaded")


def right_frame(page: Page):
    """
    右フレーム（検索フォーム/検索結果を表示するフレーム）を中身で特定して返す。
    - フォーム系要素 or 『次へ』が見えるフレームを優先
    """
    # 1) フォーム要素で探す
    for f in page.frames:
        if f is page.main_frame:
            continue
        try:
            if f.locator(
                f"{SEARCH_BTN_SELECTOR}, select, input[type='checkbox'], text=予約状況, text=複数日表示"
            ).first.is_visible(timeout=500):
                return f
        except Exception:
            pass

    # 2) 『次へ』で探す
    for f in page.frames:
        if f is page.main_frame:
            continue
        try:
            if f.locator(NEXT_BTN_SELECTOR).first.is_visible(timeout=500):
                return f
        except Exception:
            pass

    # 3) なければメイン
    return page.main_frame


def go_to_availability_menu(page: Page) -> bool:
    """
    2枚目（/gml_init）で、左メニュー『空き状況の確認』リンクをクリックして
    検索フォーム側へ遷移。見つかれば True。
    """
    selectors = [
        "a[href*='gml_z_group_sel_1']",
        "a:has-text('空き状況の確認')",
        "text=空き状況の確認",
    ]
    # すべてのフレームを横断
    for sel in selectors:
        for f in page.frames:
            try:
                loc = f.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=500):
                    loc.click(timeout=STEP_TIMEOUT_SEC * 1000)
                    page.wait_for_load_state("domcontentloaded")
                    return True
            except Exception:
                pass
    # フォールバック：ページ直下
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=500):
                loc.click(timeout=STEP_TIMEOUT_SEC * 1000)
                page.wait_for_load_state("domcontentloaded")
                return True
        except Exception:
            pass
    return False


# ===== form handling =====
def _click_nearby_confirm(container_locator):
    """
    コンテナ内で『確定・全検索』→『確定』の順にボタン候補を探してクリック。
    """
    btn = container_locator.locator(
        "button:has-text('確定・全検索'), "
        "input[type='submit'][value*='確定・全検索'], "
        "input[type='button'][value*='確定・全検索']"
    ).first
    if btn.count() == 0:
        btn = container_locator.locator(
            "button:has-text('確定'), "
            "input[type='submit'][value*='確定'], "
            "input[type='button'][value*='確定'], "
            "img[alt='確定']"
        ).first
    btn.click(timeout=STEP_TIMEOUT_SEC * 1000)


def prepare_form(f, run_dir: Path, logger):
    """
    検索フォームの初期化：
      - 分類1：『CATEGORY1_LABEL』を選択 → 近傍の「確定」
      - 目的：『PURPOSE_LABEL』を選択 → 近傍の「確定・全検索」優先
      - 曜日：『日』『土』『祝』にチェック
    """
    # 事前に「フォームっぽい要素」があるか軽く確認
    try:
        has_form = f.locator(
            "select, input, button, img[alt='検索'], text=予約状況, text=複数日表示"
        ).first.is_visible(timeout=1000)
    except Exception:
        has_form = False
    if not has_form:
        # 全フレームから再探索（語をヒントに）
        page = f.page
        for ff in page.frames:
            try:
                if ff.locator(
                    "text=屋内スポーツ施設, text=文化施設, text=バレーボール, text=予約状況, text=複数日表示"
                ).first.is_visible(timeout=500):
                    f = ff
                    break
            except Exception:
                pass

    # --- 分類1：CATEGORY1_LABEL → 近傍の「確定」を押す ---
    try:
        sel1 = f.locator(f"select:has(option:has-text('{CATEGORY1_LABEL}'))").first
        sel1.select_option(label=CATEGORY1_LABEL)
        time.sleep(0.1)  # 反映待ち
        container1 = sel1.locator("xpath=ancestor::*[self::form or self::table or self::div][1]")
        _click_nearby_confirm(container1)
        time.sleep(0.3)  # 反映待ち
    except Exception as e:
        logger(f"[warn] 分類1 '{CATEGORY1_LABEL}' の選択に失敗: {e}")

    # --- 目的：PURPOSE_LABEL → 近傍の「確定・全検索」を優先して押す ---
    try:
        sel2 = f.locator(f"select:has(option:has-text('{PURPOSE_LABEL}'))").first
        sel2.select_option(label=PURPOSE_LABEL)
        time.sleep(0.1)  # 反映待ち

        container2 = sel2.locator("xpath=ancestor::*[self::form or self::table or self::div][1]")
        _click_nearby_confirm(container2)
        time.sleep(0.3)
    except Exception as e:
        logger(f"[warn] 目的 '{PURPOSE_LABEL}' の確定に失敗: {e}")

    # --- 曜日：日・土・祝（インデックス指定で確実にチェック） ---
    try:
        # form[name='formDate'] 内の chkbox は配列（0=日,1=月,2=火,3=水,4=木,5=金,6=土,7=祝日）
        chkboxes = f.locator("form[name='formDate'] input[name='chkbox']")
        count = chkboxes.count()
        for idx in [0, 6, 7]:  # 日・土・祝
            if count > idx:
                cb = chkboxes.nth(idx)
                if cb.is_visible() and not cb.is_checked():
                    cb.check()
        time.sleep(0.15)  # hidden の u_yobi 更新待ち
    except Exception as e:
        logger(f"[warn] 曜日チェック(日・土・祝)に失敗: {e}")

    # フォームの状態を保存（デバッグ用）
    save_text(run_dir / "availability-form.html", f.content())


def submit_search(f, logger):
    """検索ボタンを押す（フレーム内）。見えなければ諦める。"""
    btn = f.locator(SEARCH_BTN_SELECTOR).first
    try:
        if not btn.is_visible(timeout=500):
            logger("[warn] 検索ボタンが見えないためスキップ")
            return
    except Exception:
        logger("[warn] 検索ボタンの可視チェックに失敗（スキップ）")
        return
    try:
        btn.click(timeout=1000)
    except Exception as e:
        logger(f"[warn] 検索ボタンのクリック失敗: {e}")


# ===== recovery guards =====
def access_denied_guard(page: Page, logger):
    """『アクセス権限がありません』画面が出たら、開始URLへ戻る。"""
    try:
        if page.get_by_text("アクセス権限がありません").first.is_visible(timeout=500):
            logger("[info] access denied screen detected -> go back to gin_menu")
            goto_menu(page)
            return True
    except Exception:
        pass
    return False


# ===== paging =====
def next_page(f) -> bool:
    """
    『次へ』が“見えて”いて“押せる”ときだけクリックして True。
    見えない/無効/押せないなら False（＝巡回終了）。
    """
    btn = f.locator(NEXT_BTN_SELECTOR).first
    # 1) ないなら終了
    if btn.count() == 0:
        return False

    # 2) 不可視/無効なら終了（ここで待たない）
    try:
        if not btn.is_visible(timeout=200):
            return False
    except Exception:
        return False
    try:
        if not btn.is_enabled():
            return False
    except Exception:
        # is_enabled が例外でも“押せない”とみなす
        return False

    # 3) クリックを短時間で試す。失敗したら終了（再試行しない）
    try:
        btn.click(timeout=500)
        return True
    except Exception:
        return False
