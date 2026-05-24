import argparse
import html
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage


def read_body(args: argparse.Namespace) -> str:
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as handle:
            return handle.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --body-file or pipe the email body on stdin.")


def linkify(value: str) -> str:
    escaped = html.escape(value)
    return re.sub(
        r"https?://[^\s\uff1b；]+",
        lambda match: f'<a href="{match.group(0)}">{match.group(0)}</a>',
        escaped,
    )


def build_html(body: str) -> str:
    css = """
    body{margin:0;background:#f6f7f9;color:#1f2933;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;line-height:1.58}
    .wrap{max-width:880px;margin:0 auto;padding:24px 18px 36px}
    h1{font-size:24px;margin:0 0 18px;color:#0f172a}
    h2{font-size:18px;margin:28px 0 12px;padding-top:4px;border-top:1px solid #d8dee8;color:#111827}
    .card{background:#fff;border:1px solid #dbe3ef;border-radius:8px;padding:14px 16px;margin:12px 0}
    .card h3{font-size:16px;margin:0 0 8px;color:#0f172a}
    p{margin:6px 0}
    ul{margin:8px 0 14px 22px;padding:0}
    li{margin:4px 0}
    .field strong{display:inline-block;min-width:74px;color:#526070}
    a{color:#1b66c9;text-decoration:none;word-break:break-all}
    """
    parts = [f"<!doctype html><html><head><meta charset=\"utf-8\"><style>{css}</style></head><body><div class=\"wrap\">"]
    card_open = False
    list_open = False

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            parts.append("</ul>")
            list_open = False

    def close_card() -> None:
        nonlocal card_open
        close_list()
        if card_open:
            parts.append("</div>")
            card_open = False

    for line_no, line in enumerate(body.splitlines()):
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        item_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if line_no == 0:
            close_card()
            parts.append(f"<h1>{html.escape(stripped)}</h1>")
        elif item_match:
            close_card()
            card_open = True
            parts.append(f"<div class=\"card\"><h3>{html.escape(item_match.group(1))}. {html.escape(item_match.group(2))}</h3>")
        elif stripped.startswith("- "):
            if not list_open:
                parts.append("<ul>")
                list_open = True
            parts.append(f"<li>{linkify(stripped[2:])}</li>")
        elif not line.startswith(" "):
            close_card()
            parts.append(f"<h2>{html.escape(stripped)}</h2>")
        elif "\uff1a" in stripped:
            label, value = stripped.split("\uff1a", 1)
            parts.append(f"<p class=\"field\"><strong>{html.escape(label)}：</strong>{linkify(value)}</p>")
        else:
            parts.append(f"<p>{linkify(stripped)}</p>")

    close_card()
    parts.append("</div></body></html>")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send the AI digest email via 163 SMTP.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file")
    parser.add_argument("--to", default=os.getenv("AI_DIGEST_EMAIL_TO", "1530550584@qq.com"))
    parser.add_argument("--from-addr", default=os.getenv("AI_DIGEST_SMTP_USER", "huanghongwei0308@163.com"))
    args = parser.parse_args()

    smtp_host = os.getenv("AI_DIGEST_SMTP_HOST", "smtp.163.com").strip()
    smtp_port = int(os.getenv("AI_DIGEST_SMTP_PORT", "465").strip())
    smtp_user = os.getenv("AI_DIGEST_SMTP_USER", args.from_addr).strip()
    smtp_password = (os.getenv("AI_DIGEST_SMTP_AUTH_CODE") or "").strip()

    if not smtp_password:
        raise SystemExit("Missing AI_DIGEST_SMTP_AUTH_CODE. Use the 163 client authorization code, not the login password.")

    message = EmailMessage()
    message["From"] = args.from_addr
    message["To"] = args.to
    message["Subject"] = args.subject
    body = read_body(args)
    message.set_content(body, charset="utf-8")
    message.add_alternative(build_html(body), subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    print(f"Sent email to {args.to}")


if __name__ == "__main__":
    main()
