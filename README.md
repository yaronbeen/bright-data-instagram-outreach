# Instagram Profile Email Scraper

Enrich Instagram profiles at scale. Give it a list of usernames (or profile URLs), get back a CSV with emails, follower counts, bio links, and business info.

**Powered by [Bright Data](https://get.brightdata.com/1tndi4600b25) Instagram datasets.**

## What It Does

```
Your Profiles List --> Bright Data Instagram API --> Scrape Profiles --> Extract Emails --> CSV File
```

1. You provide a list of Instagram usernames or profile URLs
2. The script sends them to Bright Data's Instagram Profiles dataset
3. Bright Data scrapes each profile for contact info (bio, email, links, followers)
4. The script extracts email addresses and bio links using pattern matching
5. Everything gets saved to a clean CSV file

## Example Results

Running with profiles `garyvee`, `hubspot`, `nike`, `natgeo`, `therock`:

| Username | Followers   | Email | Bio Link    | Business |
| -------- | ----------- | ----- | ----------- | -------- |
| garyvee  | 10,100,000  | —     | garyvee.com | yes      |
| hubspot  | 435,000     | —     | hubspot.com | yes      |
| nike     | 304,000,000 | —     | nike.com    | yes      |
| natgeo   | 283,000,000 | —     | natgeo.com  | yes      |
| therock  | 395,000,000 | —     | therock.com | yes      |

**From 5 profiles: 5 enriched, all business accounts identified.**

Not every profile lists an email publicly. Typical results: **10-15% of profiles** will have an email in their bio. Business accounts and smaller creators are more likely to list contact info.

## Requirements

- **Python 3.9 or higher** (comes pre-installed on most Macs; [download for Windows](https://www.python.org/downloads/))
- **Bright Data account** with API access ([sign up here](https://get.brightdata.com/1tndi4600b25) - you'll get extra credits when signing up through this link)
- No extra libraries needed - uses only Python built-in modules

## Setup (5 minutes)

### Step 1: Get Your Bright Data API Key

1. Log into [Bright Data](https://get.brightdata.com/1tndi4600b25)
2. Go to **Settings > Account settings**
3. Copy your **API token**

### Step 2: Set Your API Key

**On Windows** (Command Prompt):

```
set BRIGHT_DATA_API_KEY=your-api-key-here
```

**On Windows** (PowerShell):

```
$env:BRIGHT_DATA_API_KEY = "your-api-key-here"
```

**On Mac/Linux** (Terminal):

```
export BRIGHT_DATA_API_KEY=your-api-key-here
```

### Step 3: Prepare Your Profiles List

Edit `profiles.csv` with any text editor (Notepad, TextEdit, etc.):

```
username
garyvee
hubspot
nike
natgeo
therock
```

You can also use full URLs:

```
url
https://www.instagram.com/garyvee/
https://www.instagram.com/hubspot/
```

Or mix both formats — the script auto-detects:

```
profile
garyvee
https://www.instagram.com/hubspot/
@nike
```

## How to Run

Open your terminal/command prompt, navigate to this folder, and run:

```
python instagram_influencer_scraper.py profiles.csv output_influencers.csv
```

Or simply:

```
python instagram_influencer_scraper.py
```

This uses the built-in default profiles and saves to `output_influencers.csv`.

### What You'll See

```
[1/5] Reading profiles from profiles.csv
  Profiles to enrich: 6
    garyvee
    hubspot
    nike
    natgeo
    therock
    chfrankgrillo

[2/5] Triggering Bright Data Instagram Profiles collection...
  Username-based profiles: 6
  Triggering collection with 6 input(s)...
  Snapshot ID: sd_abc123xyz

[3/5] Waiting for collection(s) to complete (this may take 2-5 minutes)...
  Status: running (0s elapsed)
  Status: ready (15s elapsed)
  Downloading results...
  Got 6 results (5 profiles, 1 errors)

[4/5] Extracting contact info from 6 profiles...
  Enriched 5 profiles
  Emails found: 0
  Business accounts: 5

[5/5] Writing output to output_influencers.csv...

Done! 5 profiles written to output_influencers.csv
  Profiles with emails: 0
  Total unique emails: 0
  Business accounts: 5
```

## Output CSV Format

The output file has these columns:

| Column            | Description                                                         |
| ----------------- | ------------------------------------------------------------------- |
| `profile_url`     | Link to the Instagram profile                                       |
| `username`        | Instagram handle                                                    |
| `full_name`       | Display name                                                        |
| `followers`       | Follower count                                                      |
| `following`       | Following count                                                     |
| `posts_count`     | Number of posts                                                     |
| `is_business`     | Whether it's a business/professional account                        |
| `is_verified`     | Blue checkmark status                                               |
| `is_private`      | Whether the account is private                                      |
| `engagement_rate` | Average engagement rate (if available)                              |
| `biography`       | Bio text (first 500 characters)                                     |
| `email`           | Extracted email address(es), if found                               |
| `bio_link`        | External URL from bio (linktr.ee, website, etc.)                    |
| `category`        | Business category (e.g., "Fitness", "Food & Beverage", "Marketing") |

## How Email Extraction Works

The script checks two sources for each profile:

1. **`email_address` field** — Bright Data extracts this directly from the profile if publicly available
2. **Biography text** — regex scans the bio for email patterns like `anything@something.domain`

This catches formats like:

- `business@example.com`
- `contact.us@company.co.uk`
- `name+tag@domain.org`

**False positives are filtered out** — the script ignores patterns like image filenames (.png, .jpg), noreply addresses, and placeholder emails.

## Bio Link Detection

The script also detects **link aggregator** URLs in bios:

- linktr.ee, beacons.ai, bio.link, tap.bio
- lnk.bio, campsite.bio, stan.store, solo.to
- And many more

These bio links often lead to additional contact info, booking pages, or media kits.

## Where to Get Profiles

This tool enriches a list you already have. Here are common ways to build that list:

- **Competitor followers** — browse a competitor's followers list and copy usernames
- **Hashtag browsing** — search hashtags on Instagram and note active creators
- **Creator databases** — export from tools like Modash, HypeAuditor, or Upfluence
- **Google search** — search `site:instagram.com "your niche"` to find profiles
- **Manual curation** — build a targeted list of creators you want to work with

## Sending Emails (Google Apps Script)

The `apps_script.gs` file is a Google Apps Script that sends personalized outreach emails directly from Google Sheets.

### Setup

1. Create a Google Sheet with columns: `profile_name`, `email`, `followers`, `subject`, `body`, `status`
2. Import your scraped data into the sheet
3. Go to **Extensions > Apps Script**
4. Paste the contents of `apps_script.gs`
5. Save and refresh the sheet
6. Use the new **Outreach** menu to send emails

### Features

- Send all pending, or just the next 5
- Send a test email to yourself first
- 45-second delay between emails (avoids spam flags)
- DRY_RUN mode for testing
- Tracks sent/error/skipped status per row
- Check remaining Gmail quota

## Tips

- **Batch your profiles**: The script handles any number of profiles in one run
- **Business accounts are gold**: They're more likely to have public contact info
- **Smaller creators respond more**: Profiles with 10K-100K followers have the highest reply rates
- **Check bio links**: Even without an email, bio links often lead to contact pages
- **Runs are fast**: Typical enrichment takes 1-2 minutes for ~50 profiles
- **No rate limits to worry about**: Bright Data handles all the scraping infrastructure

## Troubleshooting

| Problem                               | Solution                                                               |
| ------------------------------------- | ---------------------------------------------------------------------- |
| `ERROR: Set your Bright Data API key` | You forgot to set the environment variable (see Setup Step 2)          |
| `HTTP 401`                            | Your API key is wrong or expired                                       |
| `HTTP 400`                            | Check that your Bright Data account has the Instagram datasets enabled |
| `Collection timed out`                | Try with fewer profiles or check your internet connection              |
| Script hangs at "Triggering..."       | The API call can take 30-60 seconds, this is normal                    |
| Profile shows as error                | The username might be misspelled or the account might be deleted       |
| No emails found                       | Normal for many profiles — try smaller creators or check bio links     |

## Cost

This uses Bright Data's **Web Scraper API** with one Instagram dataset:

- **Instagram Profiles** dataset: scrapes profile details, contact info, and bio data

Pricing depends on your Bright Data plan. A typical run with 50 profiles costs roughly a few cents.

## Disclaimer

Some links in this README are affiliate links. If you sign up for Bright Data through them, you may get extra credits on your account, and I may receive a small commission. This doesn't cost you anything extra — it helps support the project.

## License

MIT
