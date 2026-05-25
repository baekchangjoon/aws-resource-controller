"""Full-loop E2E for the HTTP API.

    POST /addresses            (mailbox created)
    SES send-email             (real mail sent)
    GET /addresses/.../messages (mailbox listed, expect 1 item)
    DELETE /addresses/...      (mailbox cleared)

Usage::

    python tests/e2e/e2e_api_full_loop.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request

import boto3

REGION = "ap-northeast-2"
SENDER = "changjoon.baek@gmail.com"


def _get_api_endpoint() -> str:
    if "TEMPSES_API_ENDPOINT" in os.environ:
        return os.environ["TEMPSES_API_ENDPOINT"]
    # Fall back to reading the Terraform output.
    import subprocess

    out = subprocess.run(
        [
            "terraform",
            f"-chdir={os.path.dirname(os.path.abspath(__file__))}/../../terraform/envs/dev",
            "output",
            "-raw",
            "api_endpoint",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") or "{}"
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body}


def main() -> int:
    api = _get_api_endpoint().rstrip("/")
    ses = boto3.client("sesv2", region_name=REGION)

    print(f"[1/5] POST {api}/addresses")
    status, body = _request("POST", f"{api}/addresses", {})
    if status != 201:
        print(f"  FAIL status={status} body={body}")
        return 1
    address = body["address"]
    print(f"  OK address={address}, expires_at={body['expires_at']}")

    print(f"[2/5] SES send-email FROM={SENDER} TO={address}")
    resp = ses.send_email(
        FromEmailAddress=SENDER,
        Destination={"ToAddresses": [address]},
        Content={
            "Simple": {
                "Subject": {"Data": "TempSES API E2E", "Charset": "UTF-8"},
                "Body": {"Text": {"Data": "End-to-end OK", "Charset": "UTF-8"}},
            }
        },
    )
    print(f"  sent MessageId={resp['MessageId']}")

    encoded = urllib.parse.quote(address, safe="")
    print(f"[3/5] GET {api}/addresses/{encoded}/messages (poll up to 90s)")
    deadline = time.time() + 90
    items: list = []
    while time.time() < deadline:
        status, body = _request("GET", f"{api}/addresses/{encoded}/messages")
        if status == 200:
            items = body.get("items", [])
            if items:
                break
        time.sleep(3)
    if not items:
        print(f"  FAIL no items within 90s, last status={status} body={body}")
        return 1
    print(f"  OK got {len(items)} item(s)")
    print(f"    from={items[0]['from']!r}")
    print(f"    subject={items[0]['subject']!r}")
    print(f"    body_text={items[0]['body_text'][:60]!r}")

    print(f"[4/5] DELETE {api}/addresses/{encoded}")
    status, body = _request("DELETE", f"{api}/addresses/{encoded}")
    if status != 204:
        print(f"  FAIL status={status} body={body}")
        return 1
    print("  OK 204")

    print(f"[5/5] GET {api}/addresses/{encoded}/messages (should be 404 after delete)")
    status, body = _request("GET", f"{api}/addresses/{encoded}/messages")
    if status != 404:
        print(f"  FAIL expected 404 after delete, got {status} {body}")
        return 1
    print("  OK 404")

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
