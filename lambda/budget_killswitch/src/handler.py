"""TempSES Budget Kill-Switch.

Triggered by an SNS message that AWS Budgets publishes when the monthly
spend crosses 100% ACTUAL. The function deactivates the active SES
Receipt Rule Set, which stops inbound mail processing entirely — by far
the largest cost multiplier this account is exposed to.

The web (CloudFront/S3) and API (HTTP API + Lambda) stacks keep running,
so an operator can inspect Cost Explorer / CloudWatch and re-enable the
rule set manually with::

    aws ses set-active-receipt-rule-set --rule-set-name tempses-dev-rules

The function is intentionally idempotent: SetActiveReceiptRuleSet with no
RuleSetName clears the active rule set, calling it again is a no-op.
"""

from __future__ import annotations

import logging
from typing import Any

import boto3

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

_ses = boto3.client("ses")


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, int]:
    LOG.warning("budget breach signal received: %s", event)
    _ses.set_active_receipt_rule_set()
    LOG.warning("SES active receipt rule set deactivated — inbound mail is now rejected")
    return {"statusCode": 200}
