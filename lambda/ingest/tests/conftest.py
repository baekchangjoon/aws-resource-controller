"""Test fixtures — moto-backed AWS clients and mail-builder helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from email.message import EmailMessage

import boto3
import pytest
from moto import mock_aws

REGION = "ap-northeast-2"
MAIL_BUCKET = "test-mail-bucket"
ADDRESSES_TABLE = "test-addresses"
MESSAGES_TABLE = "test-messages"
DLQ_URL = "https://sqs.test/queue/test-dlq"


@pytest.fixture(autouse=True)
def aws_credentials() -> Iterator[None]:
    """Force moto-friendly fake credentials so the test never hits real AWS."""
    keys = {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": REGION,
    }
    saved = {k: os.environ.get(k) for k in keys}
    os.environ.update(keys)
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture
def aws() -> Iterator[None]:
    """Stand up moto's mock for all services we touch."""
    with mock_aws():
        yield


@pytest.fixture
def env(aws: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAIL_BUCKET", MAIL_BUCKET)
    monkeypatch.setenv("ADDRESSES_TABLE", ADDRESSES_TABLE)
    monkeypatch.setenv("MESSAGES_TABLE", MESSAGES_TABLE)
    monkeypatch.setenv("MESSAGE_TTL_SECONDS", "7200")


@pytest.fixture
def s3_client(env: None):
    client = boto3.client("s3", region_name=REGION)
    client.create_bucket(
        Bucket=MAIL_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    return client


@pytest.fixture
def ddb_resource(env: None):
    resource = boto3.resource("dynamodb", region_name=REGION)
    resource.create_table(
        TableName=ADDRESSES_TABLE,
        KeySchema=[{"AttributeName": "address", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "address", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    resource.create_table(
        TableName=MESSAGES_TABLE,
        KeySchema=[
            {"AttributeName": "address", "KeyType": "HASH"},
            {"AttributeName": "message_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "address", "AttributeType": "S"},
            {"AttributeName": "message_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return resource


def build_mime(
    *,
    sender: str = "alice@example.com",
    recipient: str = "x8f9a@dev-temp-mail.com",
    subject: str = "Hello",
    body_text: str | None = "Plain text body",
    body_html: str | None = None,
    spam_verdict: str = "PASS",
    virus_verdict: str = "PASS",
    dkim_verdict: str = "PASS",
    spf_verdict: str = "PASS",
    attachments: list[tuple[str, str, bytes]] | None = None,
) -> bytes:
    """Build a raw RFC822 message with SES verdict headers.

    attachments: list of (filename, content_type, data) tuples.
    """
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["X-SES-Spam-Verdict"] = spam_verdict
    msg["X-SES-Virus-Verdict"] = virus_verdict
    msg["X-SES-DKIM-Verdict"] = dkim_verdict
    msg["X-SES-SPF-Verdict"] = spf_verdict
    msg["Message-ID"] = "<test@example.com>"

    if body_text is not None:
        msg.set_content(body_text)
    if body_html is not None:
        msg.add_alternative(body_html, subtype="html")
    for filename, ctype, data in attachments or []:
        maintype, subtype = ctype.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    return msg.as_bytes()


def put_email(s3_client, key: str, raw: bytes) -> None:
    s3_client.put_object(Bucket=MAIL_BUCKET, Key=key, Body=raw)


def s3_event(key: str) -> dict:
    """Construct an S3 ObjectCreated event payload."""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": REGION,
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": MAIL_BUCKET},
                    "object": {"key": key},
                },
            }
        ]
    }


def register_address(ddb_resource, address: str, ttl_seconds: int = 7200) -> None:
    import time

    ddb_resource.Table(ADDRESSES_TABLE).put_item(
        Item={
            "address": address,
            "created_at": "2026-05-25T00:00:00Z",
            "ttl_at": int(time.time()) + ttl_seconds,
        }
    )
