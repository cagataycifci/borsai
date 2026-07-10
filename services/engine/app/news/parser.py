"""RSS 2.0 / Atom feed parser (pure, network-free, so it is unit-testable).

Deliberately namespace-agnostic: feeds vary wildly in their namespace usage, so
we match on the *local* tag name. Handles both ``<item>`` (RSS) and ``<entry>``
(Atom) shapes, RFC-822 and ISO-8601 dates, and strips HTML from summaries.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from app.news.schemas import NewsItem

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _local(tag: str) -> str:
    """Strip any XML namespace, lower-cased (e.g. ``{ns}Title`` → ``title``)."""
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(el: ET.Element, names: set[str]) -> str | None:
    for child in el:
        if _local(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return None


def _child_link(el: ET.Element) -> str | None:
    # RSS: <link>text</link>; Atom: <link href="…"/> (prefer rel="alternate").
    fallback: str | None = None
    for child in el:
        if _local(child.tag) != "link":
            continue
        if child.text and child.text.strip():
            return child.text.strip()
        href = child.get("href")
        if href:
            if child.get("rel") in (None, "alternate"):
                return href.strip()
            fallback = fallback or href.strip()
    return fallback


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = _WS.sub(" ", _TAG.sub(" ", text)).strip()
    return cleaned[:500] or None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    dt: datetime | None = None
    try:
        dt = parsedate_to_datetime(value)  # RFC-822 (RSS)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))  # ISO (Atom)
        except ValueError:
            return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_feed(
    content: bytes | str, source: str, symbols: list[str] | None = None
) -> list[NewsItem]:
    """Parse an RSS/Atom document into :class:`NewsItem`s (skips malformed entries)."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    items: list[NewsItem] = []
    for el in root.iter():
        if _local(el.tag) not in {"item", "entry"}:
            continue
        title = _child_text(el, {"title"})
        url = _child_link(el)
        if not title or not url:
            continue
        published = _parse_date(
            _child_text(el, {"pubdate", "published", "updated", "date"})
        )
        items.append(
            NewsItem(
                source=source,
                title=_clean(title) or title,
                url=url,
                summary=_clean(_child_text(el, {"description", "summary", "content"})),
                symbols=list(symbols or []),
                published_at=published,
            )
        )
    return items
