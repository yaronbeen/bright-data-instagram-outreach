"""End-to-end tests against the live Bright Data API.

These tests hit the real API and cost money (~$0.01-0.05 per profile).
They are SKIPPED when BRIGHT_DATA_API_KEY is not set.

Run only E2E tests:
    pytest -m e2e -v

Run everything (unit + E2E):
    pytest -v
"""

import csv
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import instagram_influencer_scraper as scraper
from tests.conftest import skip_no_api_key

# Use a small set of well-known profiles to minimize cost
E2E_PROFILES = ["garyvee", "natgeo"]


@pytest.fixture
def e2e_input_csv(tmp_path):
    """Create a temp CSV with E2E test profiles."""
    path = tmp_path / "e2e_input.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username"])
        for profile in E2E_PROFILES:
            writer.writerow([profile])
    return str(path)


@pytest.fixture
def e2e_output_csv(tmp_path):
    """Return a path for E2E output CSV."""
    return str(tmp_path / "e2e_output.csv")


@pytest.mark.e2e
class TestBrightDataAPIConnection:
    """Test basic API connectivity."""

    @skip_no_api_key
    def test_api_key_is_valid(self):
        """Verify the API key authenticates successfully."""
        # A simple GET to the progress endpoint with a fake snapshot ID
        # should return 404 (not found), not 401 (unauthorized)
        url = f"{scraper.BASE_URL}/progress/fake_snapshot_id_12345"
        try:
            scraper.api_request("GET", url)
        except Exception as e:
            error_str = str(e)
            # 401 = bad key, 403 = forbidden -- both mean auth failed
            assert "401" not in error_str, "API key is invalid (HTTP 401)"
            assert "403" not in error_str, "API key is forbidden (HTTP 403)"
            # Any other error (404, 400, etc.) is fine -- means auth passed


@pytest.mark.e2e
class TestTriggerAndPoll:
    """Test triggering a collection and polling for results."""

    @skip_no_api_key
    def test_trigger_collection_returns_snapshot_id(self):
        """Trigger a small collection and get a snapshot ID back."""
        inputs = [{"user_name": "garyvee"}]
        snapshot_id = scraper.trigger_collection(
            scraper.PROFILES_DATASET_ID, inputs, discover_by="user_name"
        )
        assert snapshot_id is not None
        assert isinstance(snapshot_id, str)
        assert len(snapshot_id) > 5

    @skip_no_api_key
    def test_poll_and_download(self):
        """Trigger a 1-profile collection, poll until ready, download results."""
        inputs = [{"user_name": "natgeo"}]
        snapshot_id = scraper.trigger_collection(
            scraper.PROFILES_DATASET_ID, inputs, discover_by="user_name"
        )

        # Poll (this may take 1-3 minutes)
        scraper.poll_until_ready(snapshot_id)

        # Download
        results = scraper.download_snapshot(snapshot_id)
        assert results is not None
        assert isinstance(results, list)
        assert len(results) >= 1

        # Verify we got actual profile data
        profile = results[0]
        assert isinstance(profile, dict)
        # Should have at least some standard fields
        has_username = any(profile.get(k) for k in ["account", "username", "user_name"])
        assert has_username, (
            f"Profile missing username field. Keys: {list(profile.keys())}"
        )


@pytest.mark.e2e
class TestFullPipeline:
    """Test the complete scraping pipeline end-to-end."""

    @skip_no_api_key
    def test_full_flow_username_input(self, e2e_input_csv, e2e_output_csv):
        """Full pipeline: CSV input -> API -> enrichment -> CSV output.

        This is the main E2E test. It runs the same flow as the CLI tool
        but with a small profile set to keep costs low.
        """
        # Step 1: Read profiles
        profiles = scraper.read_profiles_csv(e2e_input_csv)
        assert len(profiles) == len(E2E_PROFILES)

        # Step 2: Normalize and trigger
        username_inputs = []
        for raw in profiles:
            input_type, value = scraper.normalize_input(raw)
            assert input_type == "user_name"
            username_inputs.append({"user_name": value})

        snapshot_id = scraper.trigger_collection(
            scraper.PROFILES_DATASET_ID,
            username_inputs,
            discover_by="user_name",
        )
        assert snapshot_id

        # Step 3: Poll and download
        scraper.poll_until_ready(snapshot_id)
        results = scraper.download_snapshot(snapshot_id)
        assert results is not None
        assert len(results) >= 1

        # Step 4: Extract contact info and build rows
        rows = []
        for pr_data in results:
            if pr_data.get("error"):
                continue

            username = (
                pr_data.get("account", "")
                or pr_data.get("username", "")
                or pr_data.get("user_name", "")
            )
            profile_url = pr_data.get("profile_url", "") or pr_data.get("url", "")
            if not profile_url and username:
                profile_url = f"https://www.instagram.com/{username}/"

            full_name = (
                pr_data.get("full_name", "")
                or pr_data.get("profile_name", "")
                or pr_data.get("name", "")
                or ""
            )
            followers = scraper.parse_follower_count(
                pr_data.get("followers", pr_data.get("follower_count", 0))
            )
            contact = scraper.extract_contact_info(pr_data)

            rows.append(
                {
                    "profile_url": profile_url,
                    "username": username,
                    "full_name": full_name,
                    "followers": followers if followers else "",
                    "following": scraper.parse_follower_count(
                        pr_data.get("following", 0)
                    ),
                    "posts_count": scraper.parse_follower_count(
                        pr_data.get("posts_count", pr_data.get("media_count", 0))
                    ),
                    "is_business": "yes" if contact["is_business"] else "no",
                    "is_verified": "yes" if pr_data.get("is_verified") else "no",
                    "is_private": "yes" if pr_data.get("is_private") else "no",
                    "engagement_rate": pr_data.get("avg_engagement", "") or "",
                    "biography": str(pr_data.get("biography", ""))[:500],
                    "email": "; ".join(contact["emails"]) if contact["emails"] else "",
                    "bio_link": contact["bio_link"],
                    "category": contact["category"],
                }
            )

        assert len(rows) >= 1, "Should have at least 1 enriched profile"

        # Step 5: Write output CSV
        fieldnames = [
            "profile_url",
            "username",
            "full_name",
            "followers",
            "following",
            "posts_count",
            "is_business",
            "is_verified",
            "is_private",
            "engagement_rate",
            "biography",
            "email",
            "bio_link",
            "category",
        ]
        with open(e2e_output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # Verify output file
        assert os.path.exists(e2e_output_csv)
        with open(e2e_output_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            output_rows = list(reader)

        assert len(output_rows) >= 1
        first = output_rows[0]

        # Structural assertions on output
        assert "profile_url" in first
        assert "username" in first
        assert first["username"], "Username should not be empty"
        assert "instagram.com" in first["profile_url"]
        assert first["is_business"] in ("yes", "no")
        assert first["is_verified"] in ("yes", "no")
        assert first["is_private"] in ("yes", "no")

    @skip_no_api_key
    def test_full_flow_url_input(self, tmp_path):
        """Test pipeline with URL-based input instead of usernames."""
        # Create input CSV with URLs
        input_path = tmp_path / "url_input.csv"
        output_path = tmp_path / "url_output.csv"
        with open(input_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["url"])
            writer.writerow(["https://www.instagram.com/natgeo/"])

        profiles = scraper.read_profiles_csv(str(input_path))
        assert len(profiles) == 1

        input_type, value = scraper.normalize_input(profiles[0])
        assert input_type == "url"

        url_inputs = [{"url": value}]
        snapshot_id = scraper.trigger_collection(
            scraper.PROFILES_DATASET_ID, url_inputs
        )
        assert snapshot_id

        scraper.poll_until_ready(snapshot_id)
        results = scraper.download_snapshot(snapshot_id)
        assert results is not None
        assert len(results) >= 1

        # Verify we got natgeo data back
        profile = results[0]
        assert isinstance(profile, dict)
        assert not profile.get("error"), (
            f"Profile returned error: {profile.get('error')}"
        )

    @skip_no_api_key
    def test_profile_data_structure(self):
        """Verify the shape of data returned by Bright Data matches expectations."""
        inputs = [{"user_name": "garyvee"}]
        snapshot_id = scraper.trigger_collection(
            scraper.PROFILES_DATASET_ID, inputs, discover_by="user_name"
        )
        scraper.poll_until_ready(snapshot_id)
        results = scraper.download_snapshot(snapshot_id)

        assert len(results) >= 1
        profile = results[0]

        # These fields should exist in the BD response (may be empty but present)
        expected_fields = {"biography", "followers", "following"}
        actual_keys = set(profile.keys())
        missing = expected_fields - actual_keys
        assert not missing, (
            f"Missing expected fields: {missing}. Actual keys: {sorted(actual_keys)}"
        )

        # Followers should be a positive number for a major account
        followers = scraper.parse_follower_count(
            profile.get("followers", profile.get("follower_count", 0))
        )
        assert followers > 1000, (
            f"Expected garyvee to have >1000 followers, got {followers}"
        )

    @skip_no_api_key
    def test_error_profile_handling(self):
        """Test that non-existent profiles return error entries, not crashes."""
        inputs = [{"user_name": "this_account_definitely_does_not_exist_xyz123abc"}]
        snapshot_id = scraper.trigger_collection(
            scraper.PROFILES_DATASET_ID, inputs, discover_by="user_name"
        )
        scraper.poll_until_ready(snapshot_id)
        results = scraper.download_snapshot(snapshot_id)

        # Should get results (possibly with error entries)
        assert results is not None
        assert isinstance(results, list)
        # If there's a result, it should either be an error or empty
        if len(results) > 0:
            entry = results[0]
            # Either it's an error entry or empty result -- both are valid
            assert isinstance(entry, dict)
