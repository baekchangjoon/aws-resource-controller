"""Test fixtures for the API Lambda."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

REGION = "ap-northeast-2"
DOMAIN = "dev-temp-mail.com"
ADDRESSES_TABLE = "test-addresses"
MESSAGES_TABLE = "test-messages"
MAIL_BUCKET = "test-mail-bucket"


@pytest.fixture(autouse=True)
def aws_credentials() -> Iterator[None]:
    saved = {
        k: os.environ.get(k)
        for k in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SECURITY_TOKEN",
            "AWS_SESSION_TOKEN",
            "AWS_DEFAULT_REGION",
        )
    }
    os.environ.update(
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
            "AWS_DEFAULT_REGION": REGION,
        }
    )
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
    with mock_aws():
        yield


@pytest.fixture
def env(aws: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOMAIN", DOMAIN)
    monkeypatch.setenv("ADDRESSES_TABLE", ADDRESSES_TABLE)
    monkeypatch.setenv("MESSAGES_TABLE", MESSAGES_TABLE)
    monkeypatch.setenv("MAIL_BUCKET", MAIL_BUCKET)
    monkeypatch.setenv("ADDRESS_TTL_SECONDS", "7200")
    monkeypatch.setenv("PRESIGN_EXPIRES_SECONDS", "300")
    monkeypatch.setenv("CORS_ORIGIN", "http://localhost:5173")


@pytest.fixture
def aws_setup(env: None):
    ddb = boto3.resource("dynamodb", region_name=REGION)
    ddb.create_table(
        TableName=ADDRESSES_TABLE,
        KeySchema=[{"AttributeName": "address", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "address", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    ddb.create_table(
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
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(
        Bucket=MAIL_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    return ddb, s3


def http_event(
    method: str,
    route: str,
    *,
    body: dict | None = None,
    path_params: dict[str, str] | None = None,
    qs_params: dict[str, str] | None = None,
) -> dict:
    """Synthesize an HTTP API v2.0 event payload."""
    return {
        "version": "2.0",
        "routeKey": f"{method} {route}",
        "rawPath": route,
        "headers": {"content-type": "application/json"},
        "queryStringParameters": qs_params,
        "pathParameters": path_params,
        "requestContext": {
            "http": {"method": method, "path": route, "sourceIp": "1.2.3.4"},
        },
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


def parse_body(response: dict) -> dict:
    body = response.get("body")
    if not body:
        return {}
    return json.loads(body)
