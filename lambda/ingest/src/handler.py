"""TempSES Lambda Ingest.

Triggered by S3 ObjectCreated:Put on ``emails/`` prefix of the mail bucket.
For each event we:

1. Read the raw RFC822 message from S3.
2. Drop the message if SES marked it spam or infected.
3. Drop the message if the recipient address is not currently active.
4. Parse the MIME parts into text/HTML bodies and sanitize the HTML.
5. Upload each attachment to ``attachments/<message_id>/<aid>/<name>``.
6. Persist a row to the ``messages`` table with a deterministic message_id
   derived from the S3 object key, so retries are idempotent.

Permanent failures bubble up to Lambda, which routes them to the SQS DLQ via
Destinations OnFailure (see terraform/modules/ingest_pipeline).
"""

from __future__ import annotations

import email
import hashlib
import logging
import os
import re
import time
from email.message import Message
from typing import Any

import bleach  # type: ignore[import-untyped]
import boto3
from botocore.exceptions import ClientError

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

# HTML sanitization allowlist (DECISIONS.md D17, DESIGN.md §7.2).
# img is intentionally NOT allowed — tracker pixels (D3).
ALLOWED_TAGS = [
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
]
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "title"],
    "abbr": ["title"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# Pre-strip <script>/<style> bodies so their inner text doesn't survive
# bleach (which would otherwise keep the inner text after stripping tags).
_SCRIPT_OR_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)

_s3 = boto3.client("s3")
_ddb = boto3.resource("dynamodb")


class _Skip(Exception):
    """Raised to abort processing of a single record without failing Lambda."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, int]:
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        try:
            _process_one(bucket, key)
        except _Skip as e:
            LOG.warning("drop key=%s reason=%s", key, e.reason)
    return {"statusCode": 200}


def _process_one(bucket: str, key: str) -> None:
    raw_bytes = _s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    msg = email.message_from_bytes(raw_bytes)

    if _header(msg, "X-SES-Spam-Verdict").upper() == "FAIL":
        raise _Skip("spam-verdict-fail")
    if _header(msg, "X-SES-Virus-Verdict").upper() == "FAIL":
        raise _Skip("virus-verdict-fail")

    recipient = _normalize(msg.get("To") or msg.get("X-Original-To") or "")
    if not recipient:
        raise _Skip("no-recipient")
    if not _is_address_active(recipient):
        raise _Skip("recipient-not-active")

    body_text, body_html_raw = _extract_body(msg)
    body_html_safe = _sanitize_html(body_html_raw) if body_html_raw else ""

    received_at_epoch = _received_at(bucket, key)
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    message_id = f"{received_at_epoch:010d}#{key_hash}"

    attachments = _store_attachments(msg, bucket, message_id)

    ttl_seconds = int(os.environ.get("MESSAGE_TTL_SECONDS", "7200"))
    ttl_at = received_at_epoch + ttl_seconds

    try:
        _ddb.Table(os.environ["MESSAGES_TABLE"]).put_item(
            Item={
                "address": recipient,
                "message_id": message_id,
                "from": _header(msg, "From"),
                "to": recipient,
                "subject": _header(msg, "Subject"),
                "received_at": received_at_epoch,
                "body_text": body_text or "",
                "body_html_safe": body_html_safe,
                "s3_raw_key": key,
                "attachments": attachments,
                "spam_verdict": _header(msg, "X-SES-Spam-Verdict"),
                "virus_verdict": _header(msg, "X-SES-Virus-Verdict"),
                "dkim_verdict": _header(msg, "X-SES-DKIM-Verdict"),
                "spf_verdict": _header(msg, "X-SES-SPF-Verdict"),
                "ttl_at": ttl_at,
            },
            ConditionExpression="attribute_not_exists(message_id)",
        )
        LOG.info("stored key=%s message_id=%s addr=%s", key, message_id, recipient)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            LOG.info("idempotent-skip key=%s message_id=%s", key, message_id)
            return
        raise


def _header(msg: Message, name: str) -> str:
    return (msg.get(name) or "").strip()


def _normalize(addr_field: str) -> str:
    """Normalize an RFC822 address field down to ``local@domain``.

    Supports comma-separated lists and ``Display Name <addr@host>`` form.
    """
    first = addr_field.split(",")[0].strip()
    if "<" in first and ">" in first:
        first = first[first.index("<") + 1 : first.index(">")]
    return first.strip().lower()


def _is_address_active(address: str) -> bool:
    table = _ddb.Table(os.environ["ADDRESSES_TABLE"])
    res = table.get_item(Key={"address": address})
    return "Item" in res


def _decode_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_body(msg: Message) -> tuple[str, str]:
    text = ""
    html = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart() or part.get_filename():
                continue
            ctype = part.get_content_type()
            decoded = _decode_payload(part)
            if ctype == "text/plain" and not text:
                text = decoded
            elif ctype == "text/html" and not html:
                html = decoded
    else:
        ctype = msg.get_content_type()
        decoded = _decode_payload(msg)
        if ctype == "text/html":
            html = decoded
        else:
            text = decoded
    return text, html


def _sanitize_html(html: str) -> str:
    pre_cleaned = _SCRIPT_OR_STYLE_RE.sub("", html)
    cleaned: str = bleach.clean(
        pre_cleaned,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned


def _received_at(bucket: str, key: str) -> int:
    """Return a stable epoch timestamp for the message.

    Uses the S3 object's LastModified — fixed at upload time — so retries
    against the same S3 object produce identical message_ids.
    """
    head = _s3.head_object(Bucket=bucket, Key=key)
    last_modified = head.get("LastModified")
    if last_modified is None:
        return int(time.time())
    return int(last_modified.timestamp())


def _store_attachments(msg: Message, bucket: str, message_id: str) -> list[dict[str, str | int]]:
    out: list[dict[str, str | int]] = []
    for i, part in enumerate(msg.walk()):
        filename = part.get_filename()
        if not filename:
            continue
        payload = part.get_payload(decode=True)
        data: bytes = payload if isinstance(payload, bytes) else b""
        aid = f"{i:03d}"
        s3_key = f"attachments/{message_id}/{aid}/{filename}"
        _s3.put_object(Bucket=bucket, Key=s3_key, Body=data)
        out.append(
            {
                "aid": aid,
                "filename": filename,
                "size": len(data),
                "content_type": part.get_content_type(),
                "s3_key": s3_key,
            }
        )
    return out
