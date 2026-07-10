"""Offline tests for the RSS/Atom feed parser."""

from __future__ import annotations

from app.news import parse_feed

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Feed</title>
  <item>
    <title>Apple rises</title>
    <link>https://ex.com/a</link>
    <description>&lt;p&gt;Apple &lt;b&gt;up&lt;/b&gt; sharply&lt;/p&gt;</description>
    <pubDate>Mon, 28 Jun 2026 10:00:00 GMT</pubDate>
  </item>
  <item>
    <title>No date item</title>
    <link>https://ex.com/b</link>
  </item>
  <item>
    <title>Missing link is skipped</title>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Tesla update</title>
    <link href="https://ex.com/t" rel="alternate"/>
    <summary>EV news</summary>
    <updated>2026-06-28T09:30:00Z</updated>
  </entry>
</feed>"""


def test_parse_rss() -> None:
    items = parse_feed(RSS, "Test")
    assert len(items) == 2  # third item (no link) skipped
    first = items[0]
    assert first.title == "Apple rises"
    assert first.url == "https://ex.com/a"
    assert first.summary == "Apple up sharply"  # HTML stripped + collapsed
    assert first.published_at is not None
    assert first.published_at.year == 2026
    assert first.published_at.tzinfo is not None
    assert items[1].published_at is None


def test_parse_atom_uses_link_href() -> None:
    items = parse_feed(ATOM, "Test", symbols=["TSLA"])
    assert len(items) == 1
    assert items[0].url == "https://ex.com/t"
    assert items[0].summary == "EV news"
    assert items[0].symbols == ["TSLA"]
    assert items[0].published_at is not None


def test_malformed_xml_returns_empty() -> None:
    assert parse_feed("<not xml", "Test") == []
    assert parse_feed("", "Test") == []
