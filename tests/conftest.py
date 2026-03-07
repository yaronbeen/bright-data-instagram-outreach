"""Shared fixtures for Instagram scraper tests."""

import os
import csv
import tempfile

import pytest

# Make the scraper module importable
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def has_api_key():
    """Check if Bright Data API key is available."""
    return bool(os.environ.get("BRIGHT_DATA_API_KEY", "").strip())


skip_no_api_key = pytest.mark.skipif(
    not has_api_key(),
    reason="BRIGHT_DATA_API_KEY not set - skipping live API test",
)


@pytest.fixture
def tmp_csv(tmp_path):
    """Create a temporary CSV file with given rows. Returns a factory function."""

    def _make_csv(header, rows):
        path = tmp_path / "input.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)
        return str(path)

    return _make_csv


@pytest.fixture
def tmp_output_path(tmp_path):
    """Return a path for output CSV."""
    return str(tmp_path / "output.csv")


@pytest.fixture
def sample_profile_data():
    """Return a realistic Bright Data Instagram profile response."""
    return {
        "account": "testcreator",
        "profile_url": "https://www.instagram.com/testcreator/",
        "full_name": "Test Creator",
        "biography": "Digital creator | Collabs: hello@testcreator.com | Check my links below",
        "followers": 52400,
        "following": 890,
        "posts_count": 312,
        "is_business_account": True,
        "is_verified": False,
        "is_private": False,
        "external_url": "https://linktr.ee/testcreator",
        "email_address": "",
        "business_category_name": "Creator",
        "avg_engagement": "3.2%",
    }


@pytest.fixture
def sample_profile_no_email():
    """Profile with no email anywhere."""
    return {
        "account": "bigbrand",
        "profile_url": "https://www.instagram.com/bigbrand/",
        "full_name": "Big Brand Official",
        "biography": "Official account. Shop now at bigbrand.com",
        "followers": 5000000,
        "following": 50,
        "posts_count": 1200,
        "is_business_account": True,
        "is_verified": True,
        "is_private": False,
        "external_url": "https://www.bigbrand.com",
        "email_address": "",
        "business_category_name": "Retail",
    }
