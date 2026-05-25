"""TempSES API Lambda.

Single Lambda fronts the HTTP API (DECISIONS.md D18). The handler dispatches
on the API Gateway v2 ``routeKey`` field and returns plain JSON.

Routes:
* ``POST   /addresses``                                 → register a new mailbox
* ``DELETE /addresses/{address}``                       → drop a mailbox
* ``GET    /addresses/{address}/messages``              → list messages for a mailbox
* ``GET    /messages/{address}/{id}/attach/{aid}``      → S3 presigned attachment URL
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

_ddb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"env var {name} is required")
    return value


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    route = event.get("routeKey", "")
    LOG.info("request route=%r", route)
    try:
        if route == "POST /addresses":
            return _create_address(event)
        if route == "DELETE /addresses/{address}":
            return _delete_address(event)
        if route == "GET /addresses/{address}/messages":
            return _list_messages(event)
        if route == "GET /messages/{address}/{id}/attach/{aid}":
            return _presign_attachment(event)
        return _resp(404, {"error": "route_not_found", "route": route})
    except Exception as e:
        LOG.exception("unhandled error")
        return _resp(500, {"error": "internal", "detail": str(e)})


# ---------- handlers ----------


def _create_address(event: dict[str, Any]) -> dict[str, Any]:
    body = _json_body(event)
    hint = (body.get("local_part_hint") or "").strip().lower()
    domain = _env("DOMAIN")
    ttl_seconds = int(_env("ADDRESS_TTL_SECONDS", "7200"))
    table = _ddb.Table(_env("ADDRESSES_TABLE"))

    if hint:
        # Hinted local part: one attempt only, 409 on collision.
        address = f"{hint}@{domain}"
        try:
            ttl_at = int(time.time()) + ttl_seconds
            table.put_item(
                Item={
                    "address": address,
                    "created_at": _iso(int(time.time())),
                    "ttl_at": ttl_at,
                },
                ConditionExpression="attribute_not_exists(address)",
            )
            return _resp(201, {"address": address, "expires_at": _iso(ttl_at)})
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return _resp(409, {"error": "address_taken", "address": address})
            raise

    for _ in range(8):
        local = _random_local_part()
        address = f"{local}@{domain}"
        try:
            ttl_at = int(time.time()) + ttl_seconds
            table.put_item(
                Item={
                    "address": address,
                    "created_at": _iso(int(time.time())),
                    "ttl_at": ttl_at,
                },
                ConditionExpression="attribute_not_exists(address)",
            )
            return _resp(201, {"address": address, "expires_at": _iso(ttl_at)})
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            # collision, try again
    return _resp(500, {"error": "exhausted_retries"})


def _delete_address(event: dict[str, Any]) -> dict[str, Any]:
    address = (event.get("pathParameters") or {}).get("address", "")
    if not address:
        return _resp(400, {"error": "missing_address"})

    table = _ddb.Table(_env("ADDRESSES_TABLE"))
    if "Item" not in table.get_item(Key={"address": address}):
        return _resp(404, {"error": "address_not_found"})
    table.delete_item(Key={"address": address})
    return _resp(204, None)


def _list_messages(event: dict[str, Any]) -> dict[str, Any]:
    address = (event.get("pathParameters") or {}).get("address", "")
    if not address:
        return _resp(400, {"error": "missing_address"})

    addresses = _ddb.Table(_env("ADDRESSES_TABLE"))
    if "Item" not in addresses.get_item(Key={"address": address}):
        return _resp(404, {"error": "address_not_found"})

    qs = event.get("queryStringParameters") or {}
    after = (qs.get("after") or "").strip()
    try:
        limit = max(1, min(int(qs.get("limit", "50")), 100))
    except ValueError:
        limit = 50

    cond = Key("address").eq(address)
    if after:
        cond = cond & Key("message_id").gt(after)

    res = _ddb.Table(_env("MESSAGES_TABLE")).query(
        KeyConditionExpression=cond,
        ScanIndexForward=True,
        Limit=limit,
    )
    items = res.get("Items", [])
    out = [
        {
            "id": it["message_id"],
            "from": it.get("from", ""),
            "subject": it.get("subject", ""),
            "received_at": int(it.get("received_at", 0)),
            "body_text": it.get("body_text", ""),
            "body_html_safe": it.get("body_html_safe", ""),
            "attachments": [
                {
                    "aid": a.get("aid"),
                    "filename": a.get("filename"),
                    "size": int(a.get("size", 0)),
                    "content_type": a.get("content_type", ""),
                }
                for a in it.get("attachments", []) or []
            ],
        }
        for it in items
    ]
    return _resp(200, {"items": out, "next_after": items[-1]["message_id"] if items else None})


def _presign_attachment(event: dict[str, Any]) -> dict[str, Any]:
    p = event.get("pathParameters") or {}
    address, message_id, aid = p.get("address"), p.get("id"), p.get("aid")
    if not (address and message_id and aid):
        return _resp(400, {"error": "missing_params"})

    res = _ddb.Table(_env("MESSAGES_TABLE")).get_item(
        Key={"address": address, "message_id": message_id}
    )
    if "Item" not in res:
        return _resp(404, {"error": "message_not_found"})
    match = next(
        (a for a in res["Item"].get("attachments", []) if a.get("aid") == aid),
        None,
    )
    if not match:
        return _resp(404, {"error": "attachment_not_found"})

    expires = int(_env("PRESIGN_EXPIRES_SECONDS", "300"))
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": _env("MAIL_BUCKET"), "Key": match["s3_key"]},
        ExpiresIn=expires,
    )
    return _resp(200, {"url": url, "expires_in": expires})


# ---------- helpers ----------


def _random_local_part() -> str:
    return secrets.token_hex(4)  # 8 lowercase hex chars


def _json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _iso(epoch: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _resp(status: int, body: Any) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": os.environ.get("CORS_ORIGIN", "*"),
        "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if status == 204 or body is None:
        return {"statusCode": status, "headers": headers, "body": ""}
    return {
        "statusCode": status,
        "headers": headers,
        "body": json.dumps(body, default=_json_default),
    }


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    raise TypeError(f"unserializable: {type(obj).__name__}")
