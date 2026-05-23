# AI Investment Digest

Daily AI startup and investment signal collector.

The workflow runs at 09:00 Asia/Shanghai and emails the digest via 163 SMTP.

## Coverage

The job collects public RSS feeds, direct search queries, site-specific search
queries, and WeChat/media-name search queries. GitHub Actions does not log in to
WeChat, so it does not crawl every original WeChat article directly. Chinese
business registration names and addresses require a licensed data source such as
Qichacha, Tianyancha, Qixin, or a similar API; without that API, the digest marks
registration details as pending verification and includes lookup links.

## Required GitHub Secrets

- `AI_DIGEST_SMTP_USER`: `huanghongwei0308@163.com`
- `AI_DIGEST_SMTP_AUTH_CODE`: 163 email client authorization code
- `AI_DIGEST_EMAIL_TO`: `1530550584@qq.com`

## Local Test

```powershell
python tools/build_ai_digest.py --no-send
```

To send locally, set the same environment variables and run:

```powershell
python tools/build_ai_digest.py
```
