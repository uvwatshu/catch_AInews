# AI Investment Digest

Daily AI startup and investment signal collector.

The workflow runs at 09:00 Asia/Shanghai and emails the digest via 163 SMTP.

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
