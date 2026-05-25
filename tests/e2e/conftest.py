"""Shared fixtures for E2E tests.

The tests run against the *deployed* dev environment. Reads endpoints
from Terraform output by default; can be overridden by env vars.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import boto3
import pytest

REGION = "ap-northeast-2"
SENDER = os.environ.get("TEMPSES_SENDER", "changjoon.baek@gmail.com")


def _tf_output(name: str) -> str:
    here = Path(__file__).resolve().parent
    tf_dir = here.parent.parent / "terraform" / "envs" / "dev"
    out = subprocess.run(
        ["terraform", f"-chdir={tf_dir}", "output", "-raw", name],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


@pytest.fixture(scope="session")
def web_url() -> str:
    return os.environ.get("TEMPSES_WEB_URL") or _tf_output("web_url")


@pytest.fixture(scope="session")
def api_endpoint() -> str:
    return os.environ.get("TEMPSES_API_ENDPOINT") or _tf_output("api_endpoint")


@pytest.fixture(scope="session")
def ses() -> Iterator[boto3.client]:
    yield boto3.client("sesv2", region_name=REGION)


@pytest.fixture(scope="session")
def sender() -> str:
    return SENDER
