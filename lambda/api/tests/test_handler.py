"""TDD tests for the HTTP API Lambda."""

from __future__ import annotations

import time

from tests.conftest import (
    ADDRESSES_TABLE,
    DOMAIN,
    MAIL_BUCKET,
    MESSAGES_TABLE,
    http_event,
    parse_body,
)

# ---------- POST /addresses ----------


def test_create_address_returns_201(aws_setup):
    from src.handler import lambda_handler

    res = lambda_handler(http_event("POST", "/addresses", body={}), None)

    assert res["statusCode"] == 201
    body = parse_body(res)
    assert body["address"].endswith(f"@{DOMAIN}")
    assert "expires_at" in body

    ddb, _ = aws_setup
    items = ddb.Table(ADDRESSES_TABLE).scan()["Items"]
    assert len(items) == 1
    assert items[0]["address"] == body["address"]


def test_create_address_retries_on_random_collision(aws_setup, monkeypatch):
    """If the first random local part collides, the handler tries again
    until it finds a free one."""
    from src import handler

    collide = "aaaaaaaa"
    free = "bbbbbbbb"
    ddb, _ = aws_setup
    ddb.Table(ADDRESSES_TABLE).put_item(
        Item={"address": f"{collide}@{DOMAIN}", "ttl_at": int(time.time()) + 60}
    )

    seq = iter([collide, free])
    monkeypatch.setattr(handler, "_random_local_part", lambda: next(seq))

    res = handler.lambda_handler(http_event("POST", "/addresses", body={}), None)
    assert res["statusCode"] == 201
    assert parse_body(res)["address"] == f"{free}@{DOMAIN}"


def test_create_address_with_hint_collision_returns_409(aws_setup):
    from src.handler import lambda_handler

    ddb, _ = aws_setup
    ddb.Table(ADDRESSES_TABLE).put_item(
        Item={"address": f"taken@{DOMAIN}", "ttl_at": int(time.time()) + 60}
    )

    res = lambda_handler(http_event("POST", "/addresses", body={"local_part_hint": "taken"}), None)
    assert res["statusCode"] == 409


# ---------- DELETE /addresses/{address} ----------


def test_delete_address_returns_204(aws_setup):
    from src.handler import lambda_handler

    addr = f"bye@{DOMAIN}"
    ddb, _ = aws_setup
    ddb.Table(ADDRESSES_TABLE).put_item(Item={"address": addr, "ttl_at": int(time.time()) + 60})

    res = lambda_handler(
        http_event("DELETE", "/addresses/{address}", path_params={"address": addr}),
        None,
    )
    assert res["statusCode"] == 204

    assert "Item" not in ddb.Table(ADDRESSES_TABLE).get_item(Key={"address": addr})


def test_delete_address_unknown_returns_404(aws_setup):
    from src.handler import lambda_handler

    res = lambda_handler(
        http_event(
            "DELETE",
            "/addresses/{address}",
            path_params={"address": f"missing@{DOMAIN}"},
        ),
        None,
    )
    assert res["statusCode"] == 404


# ---------- GET /addresses/{address}/messages ----------


def test_list_messages_empty(aws_setup):
    from src.handler import lambda_handler

    addr = f"empty@{DOMAIN}"
    ddb, _ = aws_setup
    ddb.Table(ADDRESSES_TABLE).put_item(Item={"address": addr, "ttl_at": int(time.time()) + 60})

    res = lambda_handler(
        http_event(
            "GET",
            "/addresses/{address}/messages",
            path_params={"address": addr},
        ),
        None,
    )
    assert res["statusCode"] == 200
    body = parse_body(res)
    assert body == {"items": [], "next_after": None}


def test_list_messages_pagination_after_cursor(aws_setup):
    from src.handler import lambda_handler

    addr = f"page@{DOMAIN}"
    ddb, _ = aws_setup
    ddb.Table(ADDRESSES_TABLE).put_item(Item={"address": addr, "ttl_at": int(time.time()) + 60})
    # Insert three messages with monotonically increasing SK so ordering is
    # well-defined.
    for i in (1, 2, 3):
        ddb.Table(MESSAGES_TABLE).put_item(
            Item={
                "address": addr,
                "message_id": f"000000000{i}#abc",
                "from": "alice@x",
                "subject": f"#{i}",
                "received_at": i,
                "body_text": f"body {i}",
                "body_html_safe": "",
                "attachments": [],
                "ttl_at": int(time.time()) + 3600,
            }
        )

    res = lambda_handler(
        http_event(
            "GET",
            "/addresses/{address}/messages",
            path_params={"address": addr},
        ),
        None,
    )
    body = parse_body(res)
    assert [it["subject"] for it in body["items"]] == ["#1", "#2", "#3"]
    assert body["next_after"] == "0000000003#abc"

    # Second page using the cursor — message_id > '0000000001#abc' yields 2,3.
    res2 = lambda_handler(
        http_event(
            "GET",
            "/addresses/{address}/messages",
            path_params={"address": addr},
            qs_params={"after": "0000000001#abc"},
        ),
        None,
    )
    body2 = parse_body(res2)
    assert [it["subject"] for it in body2["items"]] == ["#2", "#3"]


def test_list_messages_unknown_address_returns_404(aws_setup):
    from src.handler import lambda_handler

    res = lambda_handler(
        http_event(
            "GET",
            "/addresses/{address}/messages",
            path_params={"address": f"nobody@{DOMAIN}"},
        ),
        None,
    )
    assert res["statusCode"] == 404


# ---------- GET /messages/{address}/{id}/attach/{aid} ----------


def test_presign_attachment_returns_signed_url(aws_setup):
    from src.handler import lambda_handler

    addr = f"att@{DOMAIN}"
    message_id = "0000001000#deadbeef"
    aid = "001"
    s3_key = f"attachments/{message_id}/{aid}/hello.txt"

    ddb, s3 = aws_setup
    s3.put_object(Bucket=MAIL_BUCKET, Key=s3_key, Body=b"hello")
    ddb.Table(ADDRESSES_TABLE).put_item(Item={"address": addr, "ttl_at": int(time.time()) + 60})
    ddb.Table(MESSAGES_TABLE).put_item(
        Item={
            "address": addr,
            "message_id": message_id,
            "attachments": [
                {
                    "aid": aid,
                    "filename": "hello.txt",
                    "size": 5,
                    "content_type": "text/plain",
                    "s3_key": s3_key,
                }
            ],
            "ttl_at": int(time.time()) + 3600,
        }
    )

    res = lambda_handler(
        http_event(
            "GET",
            "/messages/{address}/{id}/attach/{aid}",
            path_params={"address": addr, "id": message_id, "aid": aid},
        ),
        None,
    )
    assert res["statusCode"] == 200
    body = parse_body(res)
    assert MAIL_BUCKET in body["url"]
    assert "X-Amz-Signature=" in body["url"]
    assert body["expires_in"] == 300


def test_presign_unknown_message_returns_404(aws_setup):
    from src.handler import lambda_handler

    res = lambda_handler(
        http_event(
            "GET",
            "/messages/{address}/{id}/attach/{aid}",
            path_params={
                "address": f"any@{DOMAIN}",
                "id": "missing",
                "aid": "001",
            },
        ),
        None,
    )
    assert res["statusCode"] == 404


# ---------- Routing & CORS ----------


def test_unknown_route_returns_404(aws_setup):
    from src.handler import lambda_handler

    res = lambda_handler(http_event("GET", "/whatever"), None)
    assert res["statusCode"] == 404


def test_cors_origin_header_present(aws_setup):
    from src.handler import lambda_handler

    res = lambda_handler(http_event("POST", "/addresses", body={}), None)
    assert res["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"
