# modules/notifier.py
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import re

Record = Dict[str, str]

PORTAL_URL = "https://yoyaku.city.nerima.tokyo.jp/stagia/reserve/gin_menu"

def _norm_time_parts(time_label: str) -> Tuple[str, str]:
    """
    '11:00–13:00' / '11:00-13:00' / '11:00～13:00' などから (start, end) を返す
    """
    if not time_label:
        return ("", "")
    t = re.sub(r"\s+", "", time_label)
    t = t.replace("～", "–").replace("-", "–")  # ハイフン類を統一
    if "–" in t:
        a, b = t.split("–", 1)
        return (a, b)
    return (t, "")

def _normalize_records(records: List[Record]) -> List[Record]:
    """
    標準形：
      { "date_iso": "YYYY-MM-DD", "start": "HH:MM", "end": "HH:MM", "facility_name": "..." }
    入力は以下どちらでもOK:
      A) {"date": "...", "time": "HH:MM–HH:MM", "facility": "..."}
      B) {"date_iso": "...", "start": "...", "end": "...", "facility_name": "..."}
    """
    out: List[Record] = []
    for r in records:
        date_iso = r.get("date_iso") or r.get("date") or ""
        if not date_iso:
            continue
        start = r.get("start", "")
        end = r.get("end", "")
        if not start and not end:
            start, end = _norm_time_parts(r.get("time", ""))
        facility = r.get("facility_name") or r.get("facility") or r.get("facility_full") or ""

        out.append({
            "date_iso": date_iso,
            "start": start,
            "end": end,
            "facility_name": facility,
        })
    return out

def _format_lines(records: List[Record]) -> str:
    # YYYY-MM-DD HH:MM–HH:MM / 施設名
    rows = []
    for r in sorted(records, key=lambda x: (x["date_iso"], x["start"], x["facility_name"])):
        time_part = r["start"] + ("–" + r["end"] if r["end"] else "")
        rows.append(f"・{r['date_iso']} {time_part} / {r['facility_name']}")
    return "\n".join(rows)

def send_mail(records: List[Record], dry_run: bool = False) -> bool:
    """
    正規化 → 差分レコード（records）をメール送信。
    成功 True / 送信しない（dry-run or 空） False
    """
    load_dotenv()

    norm = _normalize_records(records)
    if not norm or dry_run:
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    passwd = os.getenv("SMTP_PASS")
    mail_to = os.getenv("MAIL_TO")
    mail_from = os.getenv("MAIL_FROM") or user

    if not (host and port and user and passwd and mail_to and mail_from):
        raise RuntimeError("SMTP env not set properly")

    subject = f"【練馬区】新規空きあり（{len(norm)}件）"
    body = (
        "新規で空きが見つかりました：\n\n"
        f"{_format_lines(norm)}\n\n"
        "※ 検索期間は「次へ」ボタンが消えるまで（本日基準：翌々月末想定）を巡回しています。\n"
        f"\n確認・予約（公式）：{PORTAL_URL}\n"
    )

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Date"] = formatdate(localtime=True)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user, passwd)
        server.sendmail(mail_from, [mail_to], msg.as_string())
    return True
