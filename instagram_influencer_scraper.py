#!/usr/bin/env python3
"""Instagram Profile Enrichment Tool via Bright Data.

Workflow: Profiles CSV (usernames or URLs) -> BD Profiles Dataset -> Extract emails & contact info -> Output CSV

Usage:
    python instagram_influencer_scraper.py profiles.csv output_influencers.csv

Or simply:
    python instagram_influencer_scraper.py

This uses the built-in default profiles and saves to output_influencers.csv.

Requires:
    - Python 3.9+
    - Bright Data API key (set BRIGHT_DATA_API_KEY environment variable)
    - Active Bright Data subscription with Instagram datasets enabled
"""

import csv
import json
import os
import re
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ============================================================
# CONFIGURATION - Set your API key as an environment variable
# ============================================================
API_KEY = os.environ.get("BRIGHT_DATA_API_KEY", "")

# Bright Data dataset ID
PROFILES_DATASET_ID = "gd_l1vikfch901nx3by4"  # Instagram - Profiles

BASE_URL = "https://api.brightdata.com/datasets/v3"

POLL_INTERVAL = 15  # seconds between status checks
POLL_TIMEOUT = 1800  # 30 minutes max wait

# Regex pattern to find email addresses in text
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# False-positive email patterns to filter out
EMAIL_BLACKLIST_PATTERNS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    "noreply@",
    "no-reply@",
    "example.com",
    "email.com",
    "yourname@",
    "username@",
    "test@",
}

# Known link aggregator domains
LINK_AGGREGATORS = {
    "linktr.ee",
    "beacons.ai",
    "bio.link",
    "linkin.bio",
    "tap.bio",
    "lnk.bio",
    "campsite.bio",
    "hoo.be",
    "solo.to",
    "snipfeed.co",
    "stan.store",
    "linkpop.com",
    "milkshake.app",
    "carrd.co",
    "allmylinks.com",
    "bio.fm",
}

# Default profiles used when no CSV is provided
DEFAULT_PROFILES = [
    "nike",
    "natgeo",
    "garyvee",
    "hubspot",
    "therock",
    "chfrankgrillo",
]


def api_request(method, url, data=None):
    """Make an HTTP request to the Bright Data API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=180) as resp:
            raw = resp.read().decode()
            if not raw.strip():
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw.strip()
    except HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {body_text[:500]}")
        raise
    except URLError as e:
        print(f"  Network error: {e.reason}")
        raise


def read_profiles_csv(path):
    """Read Instagram usernames or profile URLs from a CSV file.

    Expected format (any of these work):
        username
        garyvee
        hubspot
        nike

    Or with URLs:
        url
        https://www.instagram.com/garyvee/
        https://www.instagram.com/hubspot/

    Or mixed:
        profile
        garyvee
        https://www.instagram.com/hubspot/
    """
    profiles = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        # Skip header row if it looks like one
        header_words = {
            "username",
            "usernames",
            "profile",
            "profiles",
            "url",
            "urls",
            "handle",
            "handles",
            "account",
            "accounts",
            "instagram",
        }
        if header and header[0].lower().strip() not in header_words:
            val = header[0].strip()
            if val:
                profiles.append(val)
        for row in reader:
            if not row or not row[0].strip():
                continue
            profiles.append(row[0].strip())
    return profiles


def normalize_input(raw_value):
    """Normalize an input value to a username or URL.

    Returns (input_type, value) where input_type is 'url' or 'user_name'.
    """
    val = raw_value.strip().lstrip("@")

    if val.startswith("http://") or val.startswith("https://"):
        # It's a URL - normalize it
        url = val.rstrip("/") + "/"
        return "url", url

    # It's a username
    return "user_name", val


def trigger_collection(dataset_id, inputs, discover_by=None):
    """Trigger a Bright Data dataset collection. Returns snapshot_id."""
    url = f"{BASE_URL}/trigger?dataset_id={dataset_id}&notify=false&include_errors=true"
    if discover_by:
        url += f"&type=discover_new&discover_by={discover_by}"
    payload = {"input": inputs}
    print(f"  Triggering collection with {len(inputs)} input(s)...")
    resp = api_request("POST", url, payload)
    if isinstance(resp, dict) and "snapshot_id" in resp:
        return resp["snapshot_id"]
    if isinstance(resp, str):
        return resp
    raise RuntimeError(f"Unexpected trigger response: {resp}")


def poll_until_ready(snapshot_id):
    """Poll Bright Data until the snapshot data is ready for download."""
    url = f"{BASE_URL}/progress/{snapshot_id}"
    start = time.time()
    last_status = None
    while time.time() - start < POLL_TIMEOUT:
        try:
            resp = api_request("GET", url)
        except HTTPError:
            time.sleep(POLL_INTERVAL)
            continue

        status = resp.get("status") if isinstance(resp, dict) else str(resp)
        if status != last_status:
            elapsed = int(time.time() - start)
            print(f"  Status: {status} ({elapsed}s elapsed)")
            last_status = status

        if status == "ready":
            time.sleep(5)  # Brief delay to ensure data is fully available
            return
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(
                f"Collection failed with status: {status}. Details: {resp}"
            )

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Collection timed out after {POLL_TIMEOUT}s")


def download_snapshot(snapshot_id, retries=3):
    """Download snapshot results as JSON. Retries if data isn't ready yet."""
    url = f"{BASE_URL}/snapshot/{snapshot_id}?format=json"
    for attempt in range(retries):
        print(
            f"  Downloading snapshot {snapshot_id} (attempt {attempt + 1}/{retries})..."
        )
        try:
            result = api_request("GET", url)
        except Exception as e:
            print(f"  Download error: {e}")
            if attempt < retries - 1:
                time.sleep(10)
                continue
            raise

        # If we got a dict with snapshot_id, data isn't ready yet
        if isinstance(result, dict) and "snapshot_id" in result:
            print(f"  Data not ready yet, retrying...")
            if attempt < retries - 1:
                time.sleep(15)
                continue
            raise RuntimeError(f"Snapshot data not available after {retries} attempts")

        if isinstance(result, list):
            return result

        print(f"  Unexpected response type: {type(result).__name__}, retrying...")
        if attempt < retries - 1:
            time.sleep(10)
            continue
        return result

    return None


def extract_emails(text):
    """Extract email addresses from text, filtering false positives."""
    if not text:
        return []
    raw = set(EMAIL_REGEX.findall(str(text)))
    filtered = []
    for email in raw:
        lower = email.lower()
        if any(pat in lower for pat in EMAIL_BLACKLIST_PATTERNS):
            continue
        filtered.append(email)
    return filtered


def detect_link_aggregator(url):
    """Check if a URL is a known link aggregator (linktr.ee, beacons.ai, etc.)."""
    if not url:
        return False
    lower = str(url).lower()
    return any(domain in lower for domain in LINK_AGGREGATORS)


def parse_follower_count(value):
    """Parse follower count from various formats to int.

    Handles: 1234, '1,234', '1.2K', '1.2M', '12K', etc.
    """
    if isinstance(value, (int, float)):
        return int(value)
    if not value:
        return 0
    s = str(value).strip().replace(",", "")
    if s.upper().endswith("K"):
        try:
            return int(float(s[:-1]) * 1_000)
        except ValueError:
            pass
    if s.upper().endswith("M"):
        try:
            return int(float(s[:-1]) * 1_000_000)
        except ValueError:
            pass
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def extract_contact_info(profile_data):
    """Extract contact info from an Instagram profile record.

    Returns dict with: emails, bio_link, is_business, category
    """
    bio = profile_data.get("biography", "") or profile_data.get("bio", "") or ""
    external_url = profile_data.get("external_url", "") or ""
    direct_email = profile_data.get("email_address", "") or ""

    # Extract emails from bio text
    emails = extract_emails(bio)

    # Add direct email if present and not a duplicate
    if direct_email and direct_email not in emails:
        emails.append(direct_email)

    # Format bio link
    if isinstance(external_url, list):
        bio_link = "; ".join(str(u) for u in external_url if u)
    else:
        bio_link = str(external_url).strip() if external_url else ""

    # Detect business account
    is_business = bool(
        profile_data.get("is_business_account")
        or profile_data.get("is_business")
        or profile_data.get("is_professional_account")
        or profile_data.get("business_category_name")
        or profile_data.get("category_name")
    )

    category = (
        profile_data.get("business_category_name", "")
        or profile_data.get("category_name", "")
        or profile_data.get("category", "")
        or ""
    )

    return {
        "emails": emails,
        "bio_link": bio_link,
        "is_business": is_business,
        "category": str(category) if category and str(category) != "None" else "",
    }


def main():
    if not API_KEY:
        print("ERROR: Set your Bright Data API key:")
        print("  Windows:  set BRIGHT_DATA_API_KEY=your-api-key-here")
        print("  Mac/Linux: export BRIGHT_DATA_API_KEY=your-api-key-here")
        print()
        print("Get your API key from: https://brightdata.com/cp/setting/users")
        sys.exit(1)

    input_csv = sys.argv[1] if len(sys.argv) > 1 else None
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "output_influencers.csv"

    # == Step 1: Get profiles ===========================================
    if input_csv and os.path.exists(input_csv):
        print(f"[1/5] Reading profiles from {input_csv}")
        raw_profiles = read_profiles_csv(input_csv)
    else:
        print("[1/5] Using default profiles (no CSV provided)")
        raw_profiles = DEFAULT_PROFILES

    print(f"  Profiles to enrich: {len(raw_profiles)}")
    for p in raw_profiles:
        print(f"    {p}")

    # == Step 2: Prepare and trigger collection =========================
    print(f"\n[2/5] Triggering Bright Data Instagram Profiles collection...")

    # Split into URL-based and username-based inputs
    url_inputs = []
    username_inputs = []

    for raw in raw_profiles:
        input_type, value = normalize_input(raw)
        if input_type == "url":
            url_inputs.append({"url": value})
        else:
            username_inputs.append({"user_name": value})

    snapshot_ids = []

    # Trigger URL-based collection (direct scrape)
    if url_inputs:
        print(f"  URL-based profiles: {len(url_inputs)}")
        sid = trigger_collection(PROFILES_DATASET_ID, url_inputs)
        snapshot_ids.append(("url", sid))
        print(f"  Snapshot ID: {sid}")

    # Trigger username-based collection (discover_by=user_name)
    if username_inputs:
        print(f"  Username-based profiles: {len(username_inputs)}")
        sid = trigger_collection(
            PROFILES_DATASET_ID, username_inputs, discover_by="user_name"
        )
        snapshot_ids.append(("user_name", sid))
        print(f"  Snapshot ID: {sid}")

    # == Step 3: Wait + download ========================================
    print(
        f"\n[3/5] Waiting for collection(s) to complete (this may take 2-5 minutes)..."
    )
    all_results = []
    for label, sid in snapshot_ids:
        print(f"\n  Polling {label} collection ({sid})...")
        poll_until_ready(sid)
        print(f"  Downloading results...")
        results = download_snapshot(sid)
        if results:
            valid = [r for r in results if isinstance(r, dict)]
            errors = [r for r in valid if r.get("error")]
            print(
                f"  Got {len(valid)} results ({len(valid) - len(errors)} profiles, {len(errors)} errors)"
            )
            for err in errors:
                err_input = err.get("input", {})
                err_uname = ""
                if isinstance(err_input, dict):
                    err_uname = err_input.get("user_name", "") or err_input.get(
                        "url", ""
                    )
                print(f"    Error: {err_uname} -> {err.get('error', 'unknown')}")
            all_results.extend(valid)

    if not all_results:
        print("  No profile data returned. Exiting.")
        return

    # == Step 4: Extract contact info ==================================
    print(f"\n[4/5] Extracting contact info from {len(all_results)} profiles...")
    rows = []
    email_count = 0
    business_count = 0

    for pr_data in all_results:
        if pr_data.get("error"):
            continue

        # Extract fields
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
        followers = parse_follower_count(
            pr_data.get("followers", pr_data.get("follower_count", 0))
        )
        following = parse_follower_count(pr_data.get("following", 0))
        posts_count = parse_follower_count(
            pr_data.get("posts_count", pr_data.get("media_count", 0))
        )
        is_verified = bool(pr_data.get("is_verified", False))
        is_private = bool(pr_data.get("is_private", False))
        biography = pr_data.get("biography", "") or pr_data.get("bio", "") or ""

        # Engagement rate
        engagement_rate = (
            pr_data.get("avg_engagement", "")
            or pr_data.get("engagement_rate", "")
            or ""
        )

        # Extract contact info
        contact = extract_contact_info(pr_data)
        email_str = "; ".join(contact["emails"]) if contact["emails"] else ""

        if contact["emails"]:
            email_count += len(contact["emails"])
        if contact["is_business"]:
            business_count += 1

        rows.append(
            {
                "profile_url": profile_url,
                "username": username,
                "full_name": full_name,
                "followers": followers if followers else "",
                "following": following if following else "",
                "posts_count": posts_count if posts_count else "",
                "is_business": "yes" if contact["is_business"] else "no",
                "is_verified": "yes" if is_verified else "no",
                "is_private": "yes" if is_private else "no",
                "engagement_rate": engagement_rate,
                "biography": str(biography)[:500],
                "email": email_str,
                "bio_link": contact["bio_link"],
                "category": contact["category"],
            }
        )

    print(f"  Enriched {len(rows)} profiles")
    print(f"  Emails found: {email_count}")
    print(f"  Business accounts: {business_count}")

    # == Step 5: Write output CSV ======================================
    print(f"\n[5/5] Writing output to {output_csv}...")
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
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! {len(rows)} profiles written to {output_csv}")
    print(f"  Profiles with emails: {sum(1 for r in rows if r['email'])}")
    print(f"  Total unique emails: {email_count}")
    print(f"  Business accounts: {business_count}")


if __name__ == "__main__":
    main()
