"""Smoke test for the deployed ingest Lambda.

Skips SES and writes a synthetic RFC822 message directly into the mail
bucket. The Lambda event hook should pick it up, parse, sanitize, and
write a row to the messages table.

Usage::

    python tests/e2e/smoke_ingest.py
"""

from __future__ import annotations

import sys
import time
from email.message import EmailMessage

import boto3
from boto3.dynamodb.conditions import Key

REGION = "ap-northeast-2"
MAIL_BUCKET = "tempses-dev-mail-322242916220"
ADDRESSES_TABLE = "tempses-dev-addresses"
MESSAGES_TABLE = "tempses-dev-messages"

ADDRESS = "smoke@dev-temp-mail.com"
KEY = f"emails/smoke-{int(time.time())}"


def main() -> int:
    s3 = boto3.client("s3", region_name=REGION)
    ddb = boto3.resource("dynamodb", region_name=REGION)
    addresses = ddb.Table(ADDRESSES_TABLE)
    messages = ddb.Table(MESSAGES_TABLE)

    print(f"[1/4] register {ADDRESS}")
    addresses.put_item(
        Item={
            "address": ADDRESS,
            "created_at": "smoke-test",
            "ttl_at": int(time.time()) + 3600,
        }
    )

    print(f"[2/4] upload synthetic message to s3://{MAIL_BUCKET}/{KEY}")
    msg = EmailMessage()
    msg["From"] = "alice@example.com"
    msg["To"] = ADDRESS
    msg["Subject"] = "TempSES smoke test"
    msg["X-SES-Spam-Verdict"] = "PASS"
    msg["X-SES-Virus-Verdict"] = "PASS"
    msg["X-SES-DKIM-Verdict"] = "PASS"
    msg["X-SES-SPF-Verdict"] = "PASS"
    msg.set_content("Hello from the smoke test.")
    msg.add_alternative(
        '<html><body><p>safe text</p><script>alert(1)</script></body></html>',
        subtype="html",
    )
    s3.put_object(Bucket=MAIL_BUCKET, Key=KEY, Body=msg.as_bytes())

    print("[3/4] poll messages table for up to 30s")
    deadline = time.time() + 30
    found = []
    while time.time() < deadline:
        res = messages.query(KeyConditionExpression=Key("address").eq(ADDRESS))
        found = res.get("Items", [])
        if found:
            break
        time.sleep(2)

    if not found:
        print("[FAIL] no message stored within timeout")
        return 1

    print(f"[4/4] received {len(found)} item(s)")
    for item in found:
        print(f"  - id={item['message_id']}")
        print(f"    from={item.get('from')!r}")
        print(f"    subject={item.get('subject')!r}")
        print(f"    body_text={item.get('body_text', '')[:80]!r}")
        body_html = item.get("body_html_safe", "")
        print(f"    body_html_safe={body_html[:120]!r}")
        assert "<script" not in body_html.lower(), "sanitizer did not strip <script>"
        assert "alert(1)" not in body_html, "sanitizer did not strip <script> contents"
        assert "safe text" in body_html, "sanitizer dropped legitimate content"
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
