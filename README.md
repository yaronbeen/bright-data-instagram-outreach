# Instagram Profile Enrichment

Have a list of Instagram accounts but no quick way to compare their public profile details? This Python script sends usernames or profile URLs to Bright Data's Instagram Profiles dataset and returns one CSV row per result, including public bio, follower information, category, website/bio link, and any email text it can extract. It helps a marketer turn a manually curated shortlist into a reviewable research sheet; it does not discover accounts, verify that an email works, or decide who will respond.

## The useful outcome

Use this when you already have candidate creators, brands, or partners and want a consistent first-pass inventory before manually reviewing their fit and contact route.

Example (illustrative input and possible output, not a live scrape):

```csv
username
sample_coach
sample_studio
```

The output contains the submitted accounts' returned profile fields. A marketer can then review whether the public category, bio, follower count, or website fits a campaign brief, and decide whether to investigate the listed contact route. An email found in a bio is only a lead to verify, not proof of permission, deliverability, or interest.

## What it does and does not do

- Enriches usernames, `@handles`, or profile URLs you provide.
- Requests public profile data through Bright Data's Instagram Profiles dataset.
- Extracts email-like strings from returned profile data and detects selected bio-link aggregators.
- Writes a CSV; it does not rank fit, discover followers/hashtag audiences, validate email addresses, or send messages.
- `apps_script.gs` is a separate, optional Google Sheets/Gmail sender. It can send actual email when a user runs it; inspect and test that script before use. The scraper itself never sends outreach.

## Start here

Requirements: Python 3.9+, internet access, and a Bright Data API token/account enabled for the Instagram Profiles dataset. The script uses Python's standard library; no `pip install` is needed. The key is read from the process environment as `BRIGHT_DATA_API_KEY`; there is no `.env` auto-loading.

Linux/macOS:

```bash
export BRIGHT_DATA_API_KEY="your-key"
python3 instagram_influencer_scraper.py profiles.csv output_influencers.csv
```

PowerShell:

```powershell
$env:BRIGHT_DATA_API_KEY = "your-key"
python instagram_influencer_scraper.py profiles.csv output_influencers.csv
```

Create `profiles.csv` with a header and one account per row:

```csv
username
sample_coach
https://www.instagram.com/sample_studio/
```

The command accepts an input path and optional output path. If no input path is supplied, the script uses its built-in example account list and writes `output_influencers.csv`; that list is for demonstration, not a recommendation. Use a valid input file because an invalid/missing path falls back to defaults.

## Output

The CSV columns are `profile_url`, `username`, `full_name`, `followers`, `following`, `posts_count`, `is_business`, `is_verified`, `is_private`, `engagement_rate`, `biography`, `email`, `bio_link`, and `category`. Bio text is limited to 500 characters. Fields may be blank or unavailable depending on what the dataset returns. Email extraction is pattern matching against returned profile fields; it cannot confirm ownership or mailbox validity.

## Cost and data handling

This makes a live Bright Data collection request for the accounts in your file. Charges, available credits, dataset access, and delivered fields depend on your Bright Data account and current pricing. Check the [Web Scraper pricing page](https://brightdata.com/pricing/web-scraper) and your account before a live run; this repository does not guarantee a fixed per-run cost. The tool does not log in to Instagram. Use public data responsibly, follow platform terms and applicable privacy/marketing laws, and retain only data you have a legitimate reason to use.

## Optional email sending

`apps_script.gs` is independent of the Python scraper. It can send email through the Google account that authorizes the script. Its sheet expects columns A-F in this order: `profile_name`, `email`, `followers`, `subject`, `body`, `status` (tab name defaults to `Sheet1`). Review recipients and message content yourself. The script includes a test-email menu item, a next-five option, and a 45-second pause; those safeguards are not a substitute for consent, compliance, or deliverability controls. Do not select bulk sending until you have reviewed the sheet and tested the script.

## Tests

The repository includes local helper tests and live end-to-end tests. Local tests need pytest but no API key:

```bash
python3 -m pip install pytest
python3 -m pytest -m "not e2e" -v
```

Live tests make Bright Data requests and may incur account usage. They are skipped when no `BRIGHT_DATA_API_KEY` is set:

```bash
python3 -m pytest -v
```

## FAQ

**Does it find Instagram creators for me?** No. Bring your own list; this enriches those profiles only.

**Will every row include an email?** No. It only extracts an email if one appears in data returned for that profile. A blank field is a normal outcome.

**Does it verify emails or estimate reply rates?** No. Neither mailbox validity nor response likelihood is measured.

**Can I run it without Bright Data?** You can inspect the code and run unit tests locally, but profile collection requires the API and an eligible dataset account.

**Is there a fixed cost?** No fixed amount is promised here. Check current pricing and account billing before collecting.

## License

MIT
