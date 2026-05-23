import argparse
import os
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Send the AI digest email via 163 SMTP.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file")
    parser.add_argument("--to", default=os.getenv("AI_DIGEST_EMAIL_TO", "1530550584@qq.com"))
    parser.add_argument("--from-addr", default=os.getenv("AI_DIGEST_SMTP_USER", "huanghongwei0308@163.com"))
    args = parser.parse_args()

    smtp_host = os.getenv("AI_DIGEST_SMTP_HOST", "smtp.163.com")
    smtp_port = int(os.getenv("AI_DIGEST_SMTP_PORT", "465"))
    smtp_user = os.getenv("AI_DIGEST_SMTP_USER", args.from_addr)
    smtp_password = os.getenv("AI_DIGEST_SMTP_AUTH_CODE")

    if not smtp_password:
        raise SystemExit("Missing AI_DIGEST_SMTP_AUTH_CODE. Use the 163 client authorization code, not the login password.")

    message = EmailMessage()
    message["From"] = args.from_addr
    message["To"] = args.to
    message["Subject"] = args.subject
    message.set_content(read_body(args), charset="utf-8")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    print(f"Sent email to {args.to}")


if __name__ == "__main__":
    main()
