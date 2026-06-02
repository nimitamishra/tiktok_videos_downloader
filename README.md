# TikTok Export Downloader

Download your TikTok videos from a [TikTok data export](https://support.tiktok.com/en/account-and-privacy/personalized-ads-and-data/requesting-your-data) (`Posts.txt` or `user_data.json`).

The export file contains direct CDN links to each video. This script reads those links and saves MP4 files locally, using the **post date** in each filename.

## Example filenames

```
TikTok video - 2025-04-05 at 01-36-32.mp4
TikTok video - 2025-04-04 at 03-11-35.mp4
```

If two posts share the exact same timestamp, the second gets a numeric suffix: `TikTok video - 2025-04-05 at 01-36-32 (2).mp4`.

## Requirements

- Python 3.10+
- A TikTok data export in **TXT** or **JSON** format

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/tiktok-export-downloader.git
cd tiktok-export-downloader
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On macOS, if you see SSL certificate errors, install `certifi` via the requirements file above (included) or run Apple's certificate installer for your Python install.

## Get your export from TikTok

1. In the TikTok app: **Profile → Menu → Settings and privacy → Account → Download your data**
2. Request your data (choose **TXT** or **JSON**). Preparation often takes a few days.
3. Download and unzip the archive. You need `Posts/Posts.txt` or `user_data.json`.

**Run this tool soon after you receive the export.** The download URLs are signed and expire (see `x-tos-expires` in each link). Expired links return HTTP 403.

## Usage

Place `Posts.txt` in `Posts/Posts.txt` (or pass any path), then:

```bash
python3 download_posts.py
```

Videos are saved to `downloaded_videos/` by default.

### Options

| Flag | Description |
|------|-------------|
| `python3 download_posts.py path/to/Posts.txt` | Custom input file |
| `-o ./my_videos` | Output directory |
| `-j 8` | Parallel downloads (default: 4) |
| `--limit 5` | Download only the first N videos (for testing) |
| `--no-skip-existing` | Re-download files that already exist |
| `--insecure` | Skip TLS verification (not recommended) |

```bash
# Test with 3 videos
python3 download_posts.py --limit 3

# JSON export
python3 download_posts.py ~/Downloads/tiktok_export/user_data.json -o ~/Videos/TikTok
```

Failed downloads are logged to `downloaded_videos/download_failures.txt`.

## What not to commit

Your TikTok export contains personal data and short-lived signed URLs. This repo's `.gitignore` excludes typical export folders and downloaded videos. Only push the script, `requirements.txt`, and this README unless you intentionally want to share export data.

## License

MIT — use and modify freely.
