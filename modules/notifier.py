# modules/notifier.py
import os
import smtplib
from email.mime.text import MIMEText

# ※ ここでは load_dotenv() を呼ばない

def send_mail(records, dry_run=True):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587") or "587")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    mail_from = os.getenv("MAIL_FROM", user or "")
    mail_to = os.getenv("MAIL_TO", "")
    subject_prefix = os.getenv("SUBJECT_PREFIX", "")

    if not (host and port and mail_to):
        raise RuntimeError("SMTP env not set properly")

    subject = f"{subject_prefix} 新規{len(records)}件" if subject_prefix else f"新規{len(records)}件"
    body = "新規で空きが見つかりました：\n\n" + "\n".join(
        f"・{r['date_iso']} {r['time']} / {r['facility']}" for r in records
    )
    body += "\n\n検索開始ページ: https://yoyaku.city.nerima.tokyo.jp/stagia/reserve/gin_menu\n"

    if dry_run:
        print("[mail] DRY-RUN\n", subject, "\n", body)
        return True

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to

    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        if user and password:
            s.login(user, password)
        s.sendmail(mail_from, [mail_to], msg.as_string())
    return True

if __name__ == "__main__":
    # ローカル確認用: 明示的に .env を読みたいならこのブロックでのみ
    try:
        from dotenv import load_dotenv  # ローカルにだけ依存
        load_dotenv()
    except Exception:
        pass
    send_mail([{"date_iso":"2025-10-04","time":"09:00–11:00","facility":"テスト"}], dry_run=True)
