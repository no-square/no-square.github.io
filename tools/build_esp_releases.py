#!/usr/bin/env python3
"""Refresh the two published ESP software cards during the Pages build."""

import os
import re
import sys
import tempfile
from html import escape
from pathlib import Path
from urllib.parse import quote

from build_announcements import fetch_releases, parse_date, release_channel


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "site" / "esp.html"
START = "    <!-- ESP_RELEASES:START -->"
END = "    <!-- ESP_RELEASES:END -->"
VERSION = re.compile(r"v?\d+\.\d+(?:\.\d+)*(?:[-_.][A-Za-z0-9][A-Za-z0-9._-]*)?", re.I)


def select_releases(releases):
    selected = {}
    for release in releases:
        tag = str(release.get("tag_name") or "")
        published = parse_date(release.get("published_at"))
        if release.get("draft") or not published or not VERSION.fullmatch(tag):
            continue
        selected[tag] = release
    return sorted(selected.values(), key=lambda r: (parse_date(r["published_at"]), r["tag_name"]), reverse=True)[:2]


def render_cards(releases):
    lines = ['    <section class="project-grid two" aria-label="Available ESP releases">']
    for index, release in enumerate(releases):
        tag = release["tag_name"]
        label = "LATEST" if index == 0 else "PREVIOUS"
        badge = f'<span class="pill pill-verified">{label}</span>' if index == 0 else label
        url = "https://github.com/no-square/a2eg/releases/tag/" + quote(tag, safe="")
        version = escape(re.sub(r"^v", "", tag, flags=re.I).replace("_", " "))
        date = parse_date(release["published_at"]).date().isoformat()
        lines.extend([
            '      <article class="project-card">',
            f'        <span class="project-number">{badge} &nbsp; {release_channel(release)} · {escape(tag)}</span>',
            f'        <h2>AION 2 ESP {version}</h2>',
            f'        <p>Published <time datetime="{date}">{date}</time>. Open the release page for downloads, compatibility information, and release details.</p>',
            f'        <a class="button button-primary" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">DOWNLOAD</a>',
            '      </article>',
        ])
    lines.append('    </section>')
    return "\n".join(lines)


def refresh(path=OUTPUT_PATH):
    source = path.read_text(encoding="utf-8")
    if source.count(START) != 1 or source.count(END) != 1 or source.index(START) >= source.index(END):
        raise ValueError("Expected exactly one ESP release card region")
    try:
        releases = select_releases(fetch_releases("no-square/a2eg"))
        if not releases:
            raise ValueError("No published ESP software releases found")
    except (OSError, ValueError, TimeoutError) as error:
        print(f"::warning::Keeping existing ESP release cards: {error}", file=sys.stderr)
        return False
    before, rest = source.split(START)
    _, after = rest.split(END)
    updated = before + START + "\n" + render_cards(releases) + "\n" + END + after
    if updated == source:
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(updated)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    print("Updated ESP release cards: " + ", ".join(r["tag_name"] for r in releases))
    return True


if __name__ == "__main__":
    refresh()
