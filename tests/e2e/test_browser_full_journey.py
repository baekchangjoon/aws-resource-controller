"""Browser-level E2E with Playwright.

Open the deployed SPA, let it acquire a new address, send a real
email via SES to that address, then wait for it to show up in the
inbox list and assert the message body renders inside the sandbox
iframe.

Skip the suite if Playwright is not installed.
"""

from __future__ import annotations

import re

import pytest

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:  # pragma: no cover - skip when playwright unavailable
    pytest.skip("playwright not installed", allow_module_level=True)


def test_full_user_journey(web_url, sender, ses):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(web_url, wait_until="networkidle")

            # The app fetches an address on mount.
            addr_el = page.get_by_test_id("current-address")
            expect(addr_el).to_be_visible(timeout=15_000)
            address = addr_el.inner_text().strip()
            assert re.match(r"^[a-z0-9]+@dev-temp-mail.com$", address), address
            print(f"acquired address={address}")

            subject = "Playwright E2E test"
            body = "Browser end-to-end verification."

            ses.send_email(
                FromEmailAddress=sender,
                Destination={"ToAddresses": [address]},
                Content={
                    "Simple": {
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                    }
                },
            )

            # The 5s poll picks up the new message; allow ample time for
            # SES → S3 → Lambda → DDB.
            page.get_by_text(subject, exact=False).wait_for(timeout=90_000)
            print("inbox shows the new message")

            page.get_by_text(subject, exact=False).click()
            iframe = page.get_by_test_id("message-iframe")
            expect(iframe).to_have_attribute("sandbox", "")
            expect(iframe).to_have_attribute("referrerpolicy", "no-referrer")
            print("iframe attributes verified")

            # Optional: peek into the iframe doc to confirm the body text is
            # rendered.
            frame = iframe.element_handle().content_frame()
            assert frame is not None
            text = frame.locator("body").inner_text()
            assert body.split(".")[0] in text, text
            print("iframe body matches")
        finally:
            browser.close()
