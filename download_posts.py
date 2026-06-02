#!/usr/bin/env python3
"""
Download videos listed in a TikTok data-export Posts.txt file.

Each post block looks like:
  Date: 2025-04-05 01:36:32 UTC
  Link: https://video-...tiktokv.us/...?...&mime_type=video_mp4&...

Videos are saved as MP4 files named with the post date, e.g.
TikTok video - 2025-04-05 at 01-36-32.mp4

Note: CDN links expire (see x-tos-expires in each URL). Run this soon after you
receive a new data export from TikTok.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def format_post_date_label(date_str: str) -> str:
    """Turn '2025-04-05 01:36:32 UTC' into '2025-04-05 at 01-36-32'."""
    cleaned = date_str.removesuffix(" UTC").strip()
    posted = datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
    return posted.strftime("%Y-%m-%d at %H-%M-%S")


@dataclass(frozen=True)
class PostEntry:
    date: str
    link: str
    variant: int = 1  # disambiguates multiple posts with the same timestamp

    @property
    def filename(self) -> str:
        label = f"TikTok video - {format_post_date_label(self.date)}"
        if self.variant > 1:
            label += f" ({self.variant})"
        return f"{label}.mp4"


def assign_unique_variants(entries: list[PostEntry]) -> list[PostEntry]:
    """Number duplicate post timestamps so filenames stay unique."""
    seen: dict[str, int] = {}
    result: list[PostEntry] = []
    for entry in entries:
        key = format_post_date_label(entry.date)
        variant = seen.get(key, 0) + 1
        seen[key] = variant
        result.append(
            PostEntry(date=entry.date, link=entry.link, variant=variant)
        )
    return result


def parse_posts_txt(path: Path) -> list[PostEntry]:
    text = path.read_text(encoding="utf-8", errors="replace")
    entries: list[PostEntry] = []
    current_date: str | None = None

    for line in text.splitlines():
        if line.startswith("Date:"):
            current_date = line.removeprefix("Date:").strip()
        elif line.startswith("Link:") and current_date:
            link = line.removeprefix("Link:").strip()
            if link:
                entries.append(PostEntry(date=current_date, link=link))
            current_date = None

    return entries


def parse_user_data_json(path: Path) -> list[PostEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    videos = data["Video"]["Videos"]["VideoList"]
    return [
        PostEntry(date=item["Date"], link=item["Link"])
        for item in videos
        if item.get("Link")
    ]


def load_entries(input_path: Path) -> list[PostEntry]:
    if input_path.name == "user_data.json" or input_path.suffix == ".json":
        return parse_user_data_json(input_path)
    return parse_posts_txt(input_path)


def ssl_context(*, insecure: bool) -> ssl.SSLContext:
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def download_one(
    entry: PostEntry,
    output_dir: Path,
    *,
    skip_existing: bool,
    retries: int,
    timeout: float,
    context: ssl.SSLContext,
) -> tuple[PostEntry, str]:
    """Returns (entry, status) where status is 'ok', 'skipped', or an error message."""
    dest = output_dir / entry.filename
    if skip_existing and dest.exists() and dest.stat().st_size > 0:
        return entry, "skipped"

    temp = dest.with_suffix(dest.suffix + ".part")
    last_error = "unknown error"

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                entry.link,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                if resp.status != 200:
                    last_error = f"HTTP {resp.status}"
                    continue
                with temp.open("wb") as out:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
            temp.replace(dest)
            return entry, "ok"
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code in (403, 404, 410):
                break
        except Exception as exc:  # noqa: BLE001 — surface any network/IO failure
            last_error = str(exc)

        if attempt < retries:
            time.sleep(min(2**attempt, 10))

    if temp.exists():
        temp.unlink()
    return entry, last_error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download TikTok videos from a data-export Posts.txt file."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="Posts/Posts.txt",
        type=Path,
        help="Path to Posts.txt or user_data.json (default: Posts/Posts.txt)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("downloaded_videos"),
        help="Folder for downloaded MP4 files (default: downloaded_videos)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=4,
        help="Parallel downloads (default: 4)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-download even if the output file already exists",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only download the first N posts (0 = all)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retries per video (default: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-request timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (not recommended)",
    )
    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    entries = load_entries(input_path)
    if not entries:
        print("No video links found in the input file.", file=sys.stderr)
        return 1

    if args.limit > 0:
        entries = entries[: args.limit]

    entries = assign_unique_variants(entries)

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(entries)} video(s). Saving to {output_dir.resolve()}")

    context = ssl_context(insecure=args.insecure)

    ok = skipped = failed = 0
    failures: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(
                download_one,
                entry,
                output_dir,
                skip_existing=not args.no_skip_existing,
                retries=args.retries,
                timeout=args.timeout,
                context=context,
            ): entry
            for entry in entries
        }
        done = 0
        for future in as_completed(futures):
            entry, status = future.result()
            done += 1
            if status == "ok":
                ok += 1
                mark = "OK"
            elif status == "skipped":
                skipped += 1
                mark = "skip"
            else:
                failed += 1
                failures.append((entry.filename, status))
                mark = f"FAIL ({status})"

            print(f"[{done}/{len(entries)}] {mark}: {entry.filename}")

    print()
    print(f"Done: {ok} downloaded, {skipped} skipped, {failed} failed.")

    if failures:
        log_path = output_dir / "download_failures.txt"
        log_path.write_text(
            "\n".join(f"{name}\t{err}" for name, err in failures) + "\n",
            encoding="utf-8",
        )
        print(f"Failure log written to {log_path}")
        if any("403" in err for _, err in failures):
            print(
                "\nMany 403 errors usually mean the signed CDN URLs have expired.\n"
                "Request a fresh TikTok data export and run this script right away."
            )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
