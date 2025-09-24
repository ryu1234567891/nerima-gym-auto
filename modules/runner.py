# modules/runner.py
import argparse, os, random, time, json, re, sys, traceback
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from .const import (
    URL_GIN_MENU, USER_AGENT, STEP_TIMEOUT_SEC, TOTAL_TIMEOUT_SEC,
    INITIAL_SLEEP_MS_MIN, INITIAL_SLEEP_MS_MAX, MAX_RETRIES
)
from .flow import (
    goto_menu, click_multifunc, right_frame,
    prepare_form, submit_search, access_denied_guard, next_page,
    go_to_availability_menu,
)
from .scraper import parse_result_html
from .diffstore import DiffStore
from .notifier import send_mail
from .artifacts import run_dir, save_text

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_TXT = "log.txt"
LOG_JSONL = "log.jsonl"


def logger_factory(runpath: Path):
    def log(line: str, level="info", event=None, obj=None):
        ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
        txt = f"{ts} {line}\n"
        (runpath / LOG_TXT).open("a", encoding="utf-8").write(txt)
        rec = {"ts": ts[1:-1], "level": level, "msg": line}
        if event:
            rec["event"] = event
        if obj is not None:
            rec["obj"] = obj
        (runpath / LOG_JSONL).open("a", encoding="utf-8").write(
            json.dumps(rec, ensure_ascii=False) + "\n"
        )
        print(line)
    return log


def acquire_lock(lock_path: Path, ttl_sec=600):
    now = time.time()
    if lock_path.exists():
        try:
            pid, started = lock_path.read_text().split("\n")[:2]
            started = float(started)
            if now - started < ttl_sec:
                return False
        except Exception:
            pass
    lock_path.write_text(f"{os.getpid()}\n{now}\n", encoding="utf-8")
    return True


def release_lock(lock_path: Path):
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception:
        pass


def _extract_selectdate(html: str) -> Optional[str]:
    """
    結果ページ内の hidden 'selectdate' の YYYYMMDD を取得（現在は未使用）。
    例: <input type="hidden" name="selectdate" value="20251011">
    """
    m = re.search(r'name="selectdate"\s+value="(\d{8})"', html)
    return m.group(1) if m else None


def crawl_once(page, runpath: Path, log):
    """
    1回分の処理（入口→条件セット→検索→ページ巡回）を実行して、
    抽出レコードの配列を返す。ここでは例外を握りつぶさない。
    """
    all_open = []

    # 初期ディレイ（マナー）
    time.sleep(random.uniform(INITIAL_SLEEP_MS_MIN/1000, INITIAL_SLEEP_MS_MAX/1000))

    # 1) 入口へ
    goto_menu(page)
    save_text(runpath / "gin_menu.html", page.content())

    # 2) 多機能操作（1枚目だけ）
    click_multifunc(page)

    # 3) 2枚目直後のスナップショット
    save_text(runpath / "gml_init.html", page.content())
    page.wait_for_load_state("domcontentloaded")
    time.sleep(0.5)

    # 4) 左メニュー『空き状況の確認』
    go_to_availability_menu(page)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(0.5)

    # 5) 右フレーム → 検索フォーム準備
    f = right_frame(page)
    prepare_form(f, runpath, log)

    # 6) 検索
    submit_search(f, log)
    page.wait_for_load_state("domcontentloaded")

    # 7) 巡回
    f = right_frame(page)
    save_text(runpath / "result-page-001.html", f.content())

    page_idx = 1
    MAX_PAGES = 120  # 念のための上限

    while True:
        html = f.content()

        # 抽出・ログ
        recs = parse_result_html(html)
        log(f"[page] {page_idx}/?? 抽出: {len(recs)}件")
        all_open.extend(recs)

        # 上限ガード
        if page_idx >= MAX_PAGES:
            log(f"[info] ページ上限 {MAX_PAGES} 到達 -> 巡回終了（安全弁）")
            break

        # 次へ（不可視/無効なら即終了）
        if not next_page(f):
            log("[info] '次へ' not found or not clickable. 巡回終了")
            break

        # 次ページ読み込み
        page.wait_for_load_state("domcontentloaded")
        page_idx += 1
        f = right_frame(page)
        save_text(runpath / f"result-page-{page_idx:03d}.html", f.content())
        time.sleep(random.uniform(0.3, 0.8))

    return all_open


def run_once(show=False, slowmo=0, dry_run=False, force_mail=False):
    runpath = run_dir(DATA_DIR)
    log = logger_factory(runpath)
    load_dotenv()  # SMTP など環境変数読み込み

    log(f"[start] show={show} slowmo={slowmo} dry_run={dry_run}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show, slow_mo=slowmo)
        ctx = browser.new_context(user_agent=USER_AGENT, timezone_id="Asia/Tokyo")
        page = ctx.new_page()

        success = False
        extracted = []

        # --- 入口〜巡回だけをリトライ対象にする ---
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                extracted = crawl_once(page, runpath, log)
                success = True
                break  # 成功したら抜ける（ここで再スタートしない）
            except Exception as e:
                log(f"[warn] attempt {attempt} failed: {e}")
                traceback.print_exc()
                if attempt >= MAX_RETRIES:
                    raise
                time.sleep(1.5 * attempt)

        # ブラウザはここで閉じる（失敗しても無視して進む）
        try:
            browser.close()
        except Exception:
            pass

    # --- 差分・通知はリトライしない＆ここで終了まで走る ---
    if success:
        prev_path = DATA_DIR / "prev.json"
        store = DiffStore(prev_path)

        try:
            new_records = store.diff(extracted)
        except Exception as e:
            print(f"[error] diff failed: {e}")
            new_records = []

        # 強制送信フラグ（CLI or 環境変数）
        env_force = os.getenv("FORCE_MAIL", "0") == "1"
        records_to_send = extracted if (force_mail or env_force) else new_records

        print(f"[diff] 新規 {len(new_records)}件")

        try:
            sent = send_mail(records_to_send, dry_run=dry_run)
            print("[mail] sent" if sent else "[mail] skipped (dry_run or 0件)")
        except Exception as e:
            print(f"[error] mail send failed: {e}")

        try:
            if not dry_run:
                # union 保存：カテゴリをまたいでも既知を保持
                store.save(extracted, mode="union")
        except Exception as e:
            print(f"[error] save prev failed: {e}")

        # ★ ここで確実に終了
        return 0

    # success=False でここに来るのは異常系のみ
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--slowmo", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-mail", action="store_true")  # ← 追加
    args = parser.parse_args()

    # 排他ロック
    lock_path = DATA_DIR / "nerima.lock"
    if not acquire_lock(lock_path):
        print("[info] another instance is running. exit.")
        return 0
    try:
        rc = run_once(show=args.show, slowmo=args.slowmo,
                      dry_run=args.dry_run, force_mail=args.force_mail)
        return rc
    finally:
        release_lock(lock_path)
