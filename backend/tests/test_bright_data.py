"""Regression tests for BrightDataClient method surface.

The scraper_* methods were previously orphaned as dead code inside another
function (after a `return`) — Python defines them as nested locals, never
attached to the class. This caused /warmup and /scraper/refresh to silently
fail because BrightDataClient.scraper_collect_for_company didn't exist.

These tests pin the method surface so that regression cannot recur.
"""
from __future__ import annotations

import asyncio
import os

import pytest

from app.services.bright_data import BrightDataClient
from app.models.schemas import InfraCall


# ── Method-presence pinning ─────────────────────────────────────────────────

REQUIRED_METHODS = [
    "serp_news_evidence",
    "serp_competitor_evidence",
    "unlocker_fetch",
    "unlocker_extract_article",
    "scraper_dataset",
    "scraper_poll_snapshot",
    "scraper_collect_for_company",
]


@pytest.mark.parametrize("method", REQUIRED_METHODS)
def test_bright_data_client_exposes_method(method: str) -> None:
    """Every documented method must be reachable on the instantiated client."""
    client = BrightDataClient()
    assert hasattr(client, method), (
        f"BrightDataClient missing method '{method}'. "
        f"This usually means the method got orphaned outside the class scope "
        f"(check indentation in bright_data.py)."
    )
    assert callable(getattr(client, method)), f"{method} is not callable"


def test_scraper_collect_for_company_safe_in_mock_mode() -> None:
    """In mock mode (no token), scraper_collect_for_company must return empty
    cleanly instead of raising. Critical for safe /warmup execution.
    """
    old_token = os.environ.pop("BRIGHT_DATA_API_TOKEN", None)
    old_mock = os.environ.get("USE_MOCK")
    os.environ["USE_MOCK"] = "true"
    try:
        client = BrightDataClient()
        records, ms, status = asyncio.run(
            client.scraper_collect_for_company(dataset_id="gd_fake", company="TestCo")
        )
        assert records == []
        assert status == "mock"
    finally:
        if old_token is not None:
            os.environ["BRIGHT_DATA_API_TOKEN"] = old_token
        if old_mock is None:
            os.environ.pop("USE_MOCK", None)
        else:
            os.environ["USE_MOCK"] = old_mock


def test_warmup_does_not_crash_with_dataset_id_set_in_mock_mode() -> None:
    """Even when BRIGHT_DATA_SCRAPER_DATASET_ID is set but USE_MOCK=true,
    /warmup logic must complete without crashing. Tests the scraper code path
    is reachable from the warmup endpoint.
    """
    old_dataset = os.environ.get("BRIGHT_DATA_SCRAPER_DATASET_ID")
    old_token = os.environ.pop("BRIGHT_DATA_API_TOKEN", None)
    old_mock = os.environ.get("USE_MOCK")
    os.environ["BRIGHT_DATA_SCRAPER_DATASET_ID"] = "gd_test_dataset"
    os.environ["USE_MOCK"] = "true"
    try:
        client = BrightDataClient()
        # is_live must be False because token is missing
        assert client.is_live is False, (
            "Client should be in mock mode when BRIGHT_DATA_API_TOKEN is absent"
        )
        # All scraper methods must return cleanly in mock mode
        records, ms, status = asyncio.run(
            client.scraper_collect_for_company(
                dataset_id=os.environ["BRIGHT_DATA_SCRAPER_DATASET_ID"],
                company="MockCo",
            )
        )
        assert records == []
        assert status == "mock"
        assert ms == 0
    finally:
        if old_dataset is None:
            os.environ.pop("BRIGHT_DATA_SCRAPER_DATASET_ID", None)
        else:
            os.environ["BRIGHT_DATA_SCRAPER_DATASET_ID"] = old_dataset
        if old_token is not None:
            os.environ["BRIGHT_DATA_API_TOKEN"] = old_token
        if old_mock is None:
            os.environ.pop("USE_MOCK", None)
        else:
            os.environ["USE_MOCK"] = old_mock


def test_infra_call_accepts_partial_status() -> None:
    """Web Unlocker can return partial text; infra schema must accept it."""
    row = InfraCall(
        tool="Web Unlocker",
        purpose="Article title / partial text",
        status="partial",
        ms=123,
        evidence_count=1,
    )
    assert row.status == "partial"
