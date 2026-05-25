"""Full-loop E2E:

    SES send-email  →  MX  →  SES Inbound  →  Receipt Rule  →  S3  →
    S3 event  →  Lambda  →  DynamoDB

The SES account is in sandbox mode, but the destination is the
``dev-temp-mail.com`` domain — which IS verified — so the send is
allowed.

Usage::

    python tests/e2e/e2e_ses_to_inbox.py
"""

from __future__ import annotations

import sys
import time

import boto3
from boto3.dynamodb.conditions import Key

REGION = "ap-northeast-2"
ADDRESSES_TABLE = "tempses-dev-addresses"
MESSAGES_TABLE = "tempses-dev-messages"

DOMAIN = "dev-temp-mail.com"
SENDER = "changjoon.baek@gmail.com"
RECIPIENT = f"e2e-{int(time.time())}@{DOMAIN}"
SUBJECT = "TempSES end-to-end test"
BODY = "Hello from the real SES E2E test."


def main() -> int:
    ses = boto3.client("sesv2", region_name=REGION)
    ddb = boto3.resource("dynamodb", region_name=REGION)

    print(f"[1/4] register address {RECIPIENT}")
    ddb.Table(ADDRESSES_TABLE).put_item(
        Item={
            "address": RECIPIENT,
            "created_at": "e2e-test",
            "ttl_at": int(time.time()) + 3600,
        }
    )

    print(f"[2/4] SES send-email FROM={SENDER} TO={RECIPIENT}")
    try:
        resp = ses.send_email(
            FromEmailAddress=SENDER,
            Destination={"ToAddresses": [RECIPIENT]},
            Content={
                "Simple": {
                    "Subject": {"Data": SUBJECT, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": BODY, "Charset": "UTF-8"}},
                }
            },
        )
    except ses.exceptions.MessageRejected as e:
        print(f"[FAIL] SES rejected: {e}")
        return 1
    print(f"  sent: MessageId={resp['MessageId']}")

    print("[3/4] poll messages table for up to 90s")
    deadline = time.time() + 90
    items: list[dict] = []
    while time.time() < deadline:
        res = ddb.Table(MESSAGES_TABLE).query(
            KeyConditionExpression=Key("address").eq(RECIPIENT)
        )
        items = res.get("Items", [])
        if items:
            break
        time.sleep(3)

    if not items:
        print(f"[FAIL] no message arrived for {RECIPIENT} within 90s")
        return 1

    print(f"[4/4] received {len(items)} item(s)")
    msg = items[0]
    print(f"  from={msg.get('from')!r}")
    print(f"  subject={msg.get('subject')!r}")
    print(f"  body_text={msg.get('body_text', '')[:80]!r}")
    print(f"  spam_verdict={msg.get('spam_verdict')!r}")
    print(f"  virus_verdict={msg.get('virus_verdict')!r}")
    print(f"  dkim_verdict={msg.get('dkim_verdict')!r}")
    print(f"  spf_verdict={msg.get('spf_verdict')!r}")

    assert SUBJECT in msg.get("subject", ""), "subject mismatch"
    assert BODY.split(".")[0] in msg.get("body_text", ""), "body mismatch"
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
