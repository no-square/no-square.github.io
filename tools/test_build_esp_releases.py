import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import build_esp_releases as cards


def release(tag, day=1, **extra):
    return dict(tag_name=tag, published_at=f"2026-11-{day:02d}T12:00:00Z", **extra)


class EspReleaseChecks(unittest.TestCase):
    def test_latest_two_software_releases_by_publication(self):
        selected = cards.select_releases([
            release("v3.0", 1, updated_at="2026-11-22T12:00:00Z"),
            release("v3.1", 10), release("v3.2-beta.1", 12, prerelease=True),
            release("a2eg-offsets-2026.11.22", 22),
            release("v3.3", 20, draft=True), release("latest", 21),
            dict(tag_name="v3.4", published_at=None),
        ])
        self.assertEqual([r["tag_name"] for r in selected], ["v3.2-beta.1", "v3.1"])

    def test_channels_labels_and_safe_generated_links(self):
        html = cards.render_cards([release("v3.2-beta.1", prerelease=True), release("v2.9.5_HF13")])
        for expected in ("LATEST", "PREVIOUS", "BETA", "HOTFIX", "AION 2 ESP 2.9.5 HF13"):
            self.assertIn(expected, html)
        self.assertIn("https://github.com/no-square/a2eg/releases/tag/v3.2-beta.1", html)
        html = cards.render_cards([release("v3.1", name='<script>bad</script>', html_url='javascript:bad')])
        self.assertNotIn("<script>", html)
        self.assertNotIn("javascript:", html)

    def test_refresh_preserves_surroundings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "esp.html"
            path.write_text("head\n" + cards.START + "\nold\n" + cards.END + "\nfooter", encoding="utf-8")
            with patch.object(cards, "fetch_releases", return_value=[release("v3.1")]):
                self.assertTrue(cards.refresh(path))
                self.assertFalse(cards.refresh(path))
            html = path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("head\n" + cards.START))
            self.assertTrue(html.endswith(cards.END + "\nfooter"))
            self.assertEqual(html.count('<article class="project-card">'), 1)

    def test_fetch_failure_or_empty_feed_preserves_existing_cards(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "esp.html"
            original = cards.START + "\nold\n" + cards.END
            path.write_text(original, encoding="utf-8")
            with patch.object(cards, "fetch_releases", side_effect=URLError("offline")):
                self.assertFalse(cards.refresh(path))
            with patch.object(cards, "fetch_releases", return_value=[]):
                self.assertFalse(cards.refresh(path))
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_missing_markers_fails_before_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "esp.html"
            path.write_text("no markers", encoding="utf-8")
            with patch.object(cards, "fetch_releases") as fetch:
                with self.assertRaises(ValueError):
                    cards.refresh(path)
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
