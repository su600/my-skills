#!/usr/bin/env python3
"""通过 Gmail SMTP 发送带附件的邮件。

用法: python3 send_mail.py <spec.json>

spec.json:
{
  "to": ["a@x.com", "b@y.com"],
  "subject": "主题",
  "plain": "纯文本正文",
  "html": "HTML 正文",
  "attachments": ["/abs/path/file.md"]
}

凭据从 /root/GMAIL_APP_PASSWORD.txt 读取，绝不打印。
"""
import json
import mimetypes
import os
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr

SENDER = os.environ["BJTU_MAIL_SENDER"]
SENDER_NAME = "Pi 编码助手"
PWD_FILE = "/root/GMAIL_APP_PASSWORD.txt"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    spec = json.load(open(sys.argv[1], encoding="utf-8"))

    to = spec["to"]
    if isinstance(to, str):
        to = [to]

    msg = EmailMessage()
    msg["From"] = formataddr((SENDER_NAME, SENDER))
    msg["To"] = ", ".join(to)
    msg["Subject"] = spec["subject"]
    msg.set_content(spec["plain"])
    if spec.get("html"):
        msg.add_alternative(spec["html"], subtype="html")

    attached = []
    for path in spec.get("attachments", []):
        if not os.path.isfile(path):
            print(f"FAIL: attachment missing: {path}")
            return
        ctype, _ = mimetypes.guess_type(path)
        if path.endswith(".md"):
            maintype, subtype = "text", "markdown"
        elif ctype:
            maintype, subtype = ctype.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(path))
        attached.append((os.path.basename(path), os.path.getsize(path)))

    if not os.path.isfile(PWD_FILE):
        print("FAIL: password file missing")
        return
    with open(PWD_FILE) as f:
        pwd = f.read().strip()
    if not pwd:
        print("FAIL: password file empty")
        return

    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=45) as s:
            s.login(SENDER, pwd)
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        print("FAIL: authentication rejected")
        return
    except smtplib.SMTPException as e:
        print("FAIL: smtp error", type(e).__name__)
        return
    except OSError as e:
        print("FAIL: network error", type(e).__name__)
        return

    print("SENT_OK")
    print("from:", SENDER)
    print("to:", ", ".join(to))
    print("subject:", spec["subject"])
    for name, size in attached:
        print(f"attachment: {name} ({size} bytes)")


if __name__ == "__main__":
    main()
