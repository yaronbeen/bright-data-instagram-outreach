"""Unit tests for pure helper functions in instagram_influencer_scraper.py.

These tests run without any API key or network access.
"""

import os
import csv
import pytest

import instagram_influencer_scraper as scraper


# ─── extract_emails ──────────────────────────────────────────


class TestExtractEmails:
    """Test email extraction from bio text."""

    def test_simple_email(self):
        assert scraper.extract_emails("contact me at hello@example.org") == [
            "hello@example.org"
        ]

    def test_multiple_emails(self):
        text = "business: biz@company.com, personal: me@gmail.com"
        result = scraper.extract_emails(text)
        assert set(result) == {"biz@company.com", "me@gmail.com"}

    def test_email_with_plus(self):
        result = scraper.extract_emails("reach me at name+tag@domain.org")
        assert "name+tag@domain.org" in result

    def test_email_with_dots(self):
        result = scraper.extract_emails("contact.us@company.co.uk")
        assert "contact.us@company.co.uk" in result

    def test_email_with_hyphens(self):
        result = scraper.extract_emails("my-email@my-domain.com")
        assert "my-email@my-domain.com" in result

    def test_no_email(self):
        assert scraper.extract_emails("no contact info here") == []

    def test_empty_string(self):
        assert scraper.extract_emails("") == []

    def test_none_input(self):
        assert scraper.extract_emails(None) == []

    def test_filters_image_files(self):
        result = scraper.extract_emails("photo@file.png and logo@brand.jpg")
        assert result == []

    def test_filters_noreply(self):
        result = scraper.extract_emails("noreply@company.com")
        assert result == []

    def test_filters_no_reply_hyphen(self):
        result = scraper.extract_emails("no-reply@notifications.com")
        assert result == []

    def test_filters_example_domain(self):
        result = scraper.extract_emails("user@example.com")
        assert result == []

    def test_filters_placeholder_emails(self):
        result = scraper.extract_emails("yourname@domain.com")
        assert result == []

    def test_filters_test_emails(self):
        result = scraper.extract_emails("test@something.com")
        assert result == []

    def test_keeps_real_email_filters_fake(self):
        text = "real@business.com and noreply@spam.com"
        result = scraper.extract_emails(text)
        assert "real@business.com" in result
        assert "noreply@spam.com" not in result

    def test_unicode_surrounding_text(self):
        result = scraper.extract_emails("DM or email: hello@brand.com")
        assert "hello@brand.com" in result


# ─── normalize_input ─────────────────────────────────────────


class TestNormalizeInput:
    """Test input normalization (username vs URL detection)."""

    def test_plain_username(self):
        assert scraper.normalize_input("garyvee") == ("user_name", "garyvee")

    def test_at_prefixed_username(self):
        assert scraper.normalize_input("@garyvee") == ("user_name", "garyvee")

    def test_https_url(self):
        input_type, value = scraper.normalize_input(
            "https://www.instagram.com/garyvee/"
        )
        assert input_type == "url"
        assert "instagram.com/garyvee/" in value

    def test_http_url(self):
        input_type, value = scraper.normalize_input("http://www.instagram.com/garyvee")
        assert input_type == "url"
        assert value.endswith("/")

    def test_url_without_trailing_slash(self):
        _, value = scraper.normalize_input("https://instagram.com/garyvee")
        assert value.endswith("/")

    def test_whitespace_stripping(self):
        assert scraper.normalize_input("  garyvee  ") == ("user_name", "garyvee")

    def test_at_with_whitespace(self):
        assert scraper.normalize_input("  @nike  ") == ("user_name", "nike")


# ─── parse_follower_count ────────────────────────────────────


class TestParseFollowerCount:
    """Test follower count parsing from various formats."""

    def test_integer(self):
        assert scraper.parse_follower_count(1234) == 1234

    def test_float(self):
        assert scraper.parse_follower_count(1234.5) == 1234

    def test_string_number(self):
        assert scraper.parse_follower_count("1234") == 1234

    def test_comma_formatted(self):
        assert scraper.parse_follower_count("1,234") == 1234

    def test_large_comma_formatted(self):
        assert scraper.parse_follower_count("1,234,567") == 1234567

    def test_k_suffix_lowercase(self):
        assert scraper.parse_follower_count("12K") == 12000

    def test_k_suffix_decimal(self):
        assert scraper.parse_follower_count("1.2K") == 1200

    def test_m_suffix(self):
        assert scraper.parse_follower_count("1.5M") == 1500000

    def test_m_suffix_whole(self):
        assert scraper.parse_follower_count("3M") == 3000000

    def test_zero(self):
        assert scraper.parse_follower_count(0) == 0

    def test_empty_string(self):
        assert scraper.parse_follower_count("") == 0

    def test_none(self):
        assert scraper.parse_follower_count(None) == 0

    def test_invalid_string(self):
        assert scraper.parse_follower_count("not a number") == 0


# ─── detect_link_aggregator ─────────────────────────────────


class TestDetectLinkAggregator:
    """Test link aggregator URL detection."""

    def test_linktree(self):
        assert scraper.detect_link_aggregator("https://linktr.ee/someone") is True

    def test_beacons(self):
        assert scraper.detect_link_aggregator("https://beacons.ai/someone") is True

    def test_bio_link(self):
        assert scraper.detect_link_aggregator("https://bio.link/creator") is True

    def test_stan_store(self):
        assert scraper.detect_link_aggregator("https://stan.store/creator") is True

    def test_campsite_bio(self):
        assert scraper.detect_link_aggregator("https://campsite.bio/me") is True

    def test_regular_url(self):
        assert scraper.detect_link_aggregator("https://www.google.com") is False

    def test_personal_website(self):
        assert scraper.detect_link_aggregator("https://mybrand.com") is False

    def test_empty_string(self):
        assert scraper.detect_link_aggregator("") is False

    def test_none(self):
        assert scraper.detect_link_aggregator(None) is False

    def test_case_insensitive(self):
        assert scraper.detect_link_aggregator("https://LINKTR.EE/someone") is True


# ─── extract_contact_info ────────────────────────────────────


class TestExtractContactInfo:
    """Test contact info extraction from profile data dicts."""

    def test_email_in_bio(self, sample_profile_data):
        result = scraper.extract_contact_info(sample_profile_data)
        assert "hello@testcreator.com" in result["emails"]

    def test_bio_link_extracted(self, sample_profile_data):
        result = scraper.extract_contact_info(sample_profile_data)
        assert "linktr.ee" in result["bio_link"]

    def test_business_detected(self, sample_profile_data):
        result = scraper.extract_contact_info(sample_profile_data)
        assert result["is_business"] is True

    def test_category_extracted(self, sample_profile_data):
        result = scraper.extract_contact_info(sample_profile_data)
        assert result["category"] == "Creator"

    def test_no_email_profile(self, sample_profile_no_email):
        result = scraper.extract_contact_info(sample_profile_no_email)
        assert result["emails"] == []

    def test_direct_email_field(self):
        """When email_address field is set by Bright Data."""
        data = {
            "biography": "No email in bio",
            "external_url": "",
            "email_address": "direct@brand.com",
            "is_business_account": True,
        }
        result = scraper.extract_contact_info(data)
        assert "direct@brand.com" in result["emails"]

    def test_both_bio_and_direct_email(self):
        """Both bio email and direct email, no duplicates."""
        data = {
            "biography": "Email me: bio@creator.com",
            "external_url": "",
            "email_address": "direct@creator.com",
            "is_business_account": False,
        }
        result = scraper.extract_contact_info(data)
        assert "bio@creator.com" in result["emails"]
        assert "direct@creator.com" in result["emails"]

    def test_duplicate_email_deduplicated(self):
        """Same email in bio and direct field should appear once."""
        data = {
            "biography": "Email: same@creator.com",
            "external_url": "",
            "email_address": "same@creator.com",
        }
        result = scraper.extract_contact_info(data)
        assert result["emails"].count("same@creator.com") == 1

    def test_external_url_as_list(self):
        """Some profiles return external_url as a list."""
        data = {
            "biography": "",
            "external_url": ["https://site1.com", "https://site2.com"],
            "email_address": "",
        }
        result = scraper.extract_contact_info(data)
        assert "site1.com" in result["bio_link"]
        assert "site2.com" in result["bio_link"]

    def test_non_business_account(self):
        data = {
            "biography": "",
            "external_url": "",
            "email_address": "",
        }
        result = scraper.extract_contact_info(data)
        assert result["is_business"] is False

    def test_business_via_category_name(self):
        data = {
            "biography": "",
            "external_url": "",
            "email_address": "",
            "category_name": "Fitness",
        }
        result = scraper.extract_contact_info(data)
        assert result["is_business"] is True
        assert result["category"] == "Fitness"

    def test_empty_profile(self):
        data = {}
        result = scraper.extract_contact_info(data)
        assert result["emails"] == []
        assert result["bio_link"] == ""
        assert result["is_business"] is False
        assert result["category"] == ""


# ─── read_profiles_csv ───────────────────────────────────────


class TestReadProfilesCsv:
    """Test CSV reading with various formats."""

    def test_username_column(self, tmp_csv):
        path = tmp_csv(["username"], [["garyvee"], ["hubspot"], ["nike"]])
        result = scraper.read_profiles_csv(path)
        assert result == ["garyvee", "hubspot", "nike"]

    def test_url_column(self, tmp_csv):
        path = tmp_csv(
            ["url"],
            [
                ["https://www.instagram.com/garyvee/"],
                ["https://www.instagram.com/hubspot/"],
            ],
        )
        result = scraper.read_profiles_csv(path)
        assert len(result) == 2
        assert "instagram.com/garyvee/" in result[0]

    def test_profile_column(self, tmp_csv):
        path = tmp_csv(["profile"], [["garyvee"], ["hubspot"]])
        result = scraper.read_profiles_csv(path)
        assert result == ["garyvee", "hubspot"]

    def test_handle_column(self, tmp_csv):
        path = tmp_csv(["handle"], [["garyvee"]])
        result = scraper.read_profiles_csv(path)
        assert result == ["garyvee"]

    def test_mixed_formats(self, tmp_csv):
        path = tmp_csv(
            ["profile"],
            [
                ["garyvee"],
                ["https://www.instagram.com/hubspot/"],
            ],
        )
        result = scraper.read_profiles_csv(path)
        assert len(result) == 2

    def test_skips_empty_rows(self, tmp_csv):
        path = tmp_csv(["username"], [["garyvee"], [""], ["hubspot"]])
        result = scraper.read_profiles_csv(path)
        assert result == ["garyvee", "hubspot"]

    def test_non_header_first_row(self, tmp_csv):
        """When first row is data, not a recognized header."""
        path = tmp_csv(["garyvee"], [["hubspot"], ["nike"]])
        result = scraper.read_profiles_csv(path)
        assert "garyvee" in result
        assert "hubspot" in result
        assert "nike" in result

    def test_whitespace_stripped(self, tmp_csv):
        path = tmp_csv(["username"], [["  garyvee  "], [" hubspot"]])
        result = scraper.read_profiles_csv(path)
        assert result == ["garyvee", "hubspot"]

    def test_actual_profiles_csv(self):
        """Read the real profiles.csv shipped with the project."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "profiles.csv",
        )
        if not os.path.exists(path):
            pytest.skip("profiles.csv not found")
        result = scraper.read_profiles_csv(path)
        assert len(result) >= 1
        assert all(isinstance(p, str) for p in result)
        assert all(len(p) > 0 for p in result)
