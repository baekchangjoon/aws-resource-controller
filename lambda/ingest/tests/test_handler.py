"""TDD test suite for the Lambda Ingest handler.

Each test exercises one branch from docs/ROADMAP.md §1.1.
"""

from __future__ import annotations

import boto3

from tests.conftest import (
    MAIL_BUCKET,
    MESSAGES_TABLE,
    build_mime,
    put_email,
    register_address,
    s3_event,
)


def _messages_for(ddb_resource, address: str) -> list[dict]:
    table = ddb_resource.Table(MESSAGES_TABLE)
    return table.query(KeyConditionExpression=boto3.dynamodb.conditions.Key("address").eq(address))[
        "Items"
    ]


def test_drop_when_spam_verdict_fail(s3_client, ddb_resource):
    from src.handler import lambda_handler

    addr = "spam-target@dev-temp-mail.com"
    register_address(ddb_resource, addr)
    put_email(
        s3_client,
        "emails/raw-spam",
        build_mime(recipient=addr, spam_verdict="FAIL"),
    )

    lambda_handler(s3_event("emails/raw-spam"), None)

    assert _messages_for(ddb_resource, addr) == []


def test_drop_when_virus_verdict_fail(s3_client, ddb_resource):
    from src.handler import lambda_handler

    addr = "virus-target@dev-temp-mail.com"
    register_address(ddb_resource, addr)
    put_email(
        s3_client,
        "emails/raw-virus",
        build_mime(recipient=addr, virus_verdict="FAIL"),
    )

    lambda_handler(s3_event("emails/raw-virus"), None)

    assert _messages_for(ddb_resource, addr) == []


def test_drop_when_address_not_active(s3_client, ddb_resource):
    from src.handler import lambda_handler

    unknown = "unregistered@dev-temp-mail.com"
    # NOTE: we deliberately do NOT call register_address — recipient is unknown.
    put_email(s3_client, "emails/raw-unknown", build_mime(recipient=unknown))

    lambda_handler(s3_event("emails/raw-unknown"), None)

    assert _messages_for(ddb_resource, unknown) == []


def test_happy_path_text_only(s3_client, ddb_resource):
    from src.handler import lambda_handler

    addr = "happy@dev-temp-mail.com"
    register_address(ddb_resource, addr)
    put_email(
        s3_client,
        "emails/raw-happy",
        build_mime(
            sender="sender@example.com",
            recipient=addr,
            subject="Hello there",
            body_text="Plain text body",
        ),
    )

    lambda_handler(s3_event("emails/raw-happy"), None)

    items = _messages_for(ddb_resource, addr)
    assert len(items) == 1
    msg = items[0]
    assert msg["from"] == "sender@example.com"
    assert msg["subject"] == "Hello there"
    assert "Plain text body" in msg["body_text"]
    assert msg["body_html_safe"] == ""
    assert msg["s3_raw_key"] == "emails/raw-happy"
    assert int(msg["ttl_at"]) > 0


def test_html_sanitized_removes_script_and_img_src(s3_client, ddb_resource):
    from src.handler import lambda_handler

    addr = "html@dev-temp-mail.com"
    register_address(ddb_resource, addr)
    html = (
        "<html><body>"
        "<p>safe text</p>"
        "<script>alert('xss')</script>"
        '<a href="https://ok" onclick="bad()">link</a>'
        '<img src="https://tracker.example.com/pixel.png" />'
        "</body></html>"
    )
    put_email(
        s3_client,
        "emails/raw-html",
        build_mime(recipient=addr, body_html=html),
    )

    lambda_handler(s3_event("emails/raw-html"), None)

    items = _messages_for(ddb_resource, addr)
    assert len(items) == 1
    body = items[0]["body_html_safe"]

    assert "<script" not in body.lower()
    assert "alert(" not in body
    assert "onclick" not in body.lower()
    # The <a href="..."> should survive, but <img> src must be stripped (D3).
    assert "tracker.example.com" not in body
    assert "safe text" in body


def test_attachment_uploaded_to_s3(s3_client, ddb_resource):
    from src.handler import lambda_handler

    addr = "att@dev-temp-mail.com"
    register_address(ddb_resource, addr)
    put_email(
        s3_client,
        "emails/raw-att",
        build_mime(
            recipient=addr,
            body_text="see attachment",
            attachments=[("hello.txt", "text/plain", b"hello world")],
        ),
    )

    lambda_handler(s3_event("emails/raw-att"), None)

    items = _messages_for(ddb_resource, addr)
    assert len(items) == 1
    attachments = items[0]["attachments"]
    assert len(attachments) == 1
    att = attachments[0]
    assert att["filename"] == "hello.txt"
    assert att["content_type"] == "text/plain"
    assert int(att["size"]) == len(b"hello world")
    assert att["s3_key"].startswith("attachments/")

    # Verify the file actually landed in S3 (with the right body).
    head = s3_client.get_object(Bucket=MAIL_BUCKET, Key=att["s3_key"])
    assert head["Body"].read() == b"hello world"


def test_idempotent_on_duplicate_s3_event(s3_client, ddb_resource):
    from src.handler import lambda_handler

    addr = "dup@dev-temp-mail.com"
    register_address(ddb_resource, addr)
    put_email(
        s3_client,
        "emails/raw-dup",
        build_mime(recipient=addr, body_text="once"),
    )

    lambda_handler(s3_event("emails/raw-dup"), None)
    lambda_handler(s3_event("emails/raw-dup"), None)

    items = _messages_for(ddb_resource, addr)
    assert len(items) == 1, f"expected idempotent insert, got {len(items)} items"
