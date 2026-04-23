"""
Resolve Roots of All Beings (Substack) post titles to URLs and validate fetched HTML.

Used by the web crawler to avoid "first hardcoded Substack URL wins" when the user
names a specific article title in their query.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

import requests

try:
    from rapidfuzz import fuzz as _rf_fuzz
except ImportError:  # pragma: no cover
    _rf_fuzz = None

def _ratio(a: str, b: str) -> float:
    if _rf_fuzz is not None:
        return float(_rf_fuzz.ratio(a, b))
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a, b).ratio() * 100.0


def _token_set_ratio(a: str, b: str) -> float:
    if _rf_fuzz is not None:
        return float(_rf_fuzz.token_set_ratio(a, b))
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 100.0
    if not sa or not sb:
        return 0.0
    inter = sa & sb
    u = " ".join(sorted(inter))
    sa_m = " ".join(sorted(sa))
    sb_m = " ".join(sorted(sb))
    return max(_ratio(u, sa_m), _ratio(u, sb_m), _ratio(sa_m, sb_m))


def _partial_ratio(a: str, b: str) -> float:
    if _rf_fuzz is not None:
        return float(_rf_fuzz.partial_ratio(a, b))
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    best = 0.0
    n = len(shorter)
    for i in range(0, len(longer) - n + 1):
        window = longer[i : i + n]
        best = max(best, _ratio(shorter, window))
    return best

ROOTS_SUBSTACK_FEED_URL = "https://rootsofallbeings.substack.com/feed"
FEED_TTL_SEC = 3600
MATCH_SCORE_MIN = 82.0

# Module-level feed cache (list of (title, url))
_feed_cache: Optional[List[Tuple[str, str]]] = None
_feed_cache_at: float = 0.0


def clear_roots_feed_cache() -> None:
    """Clear in-memory feed cache (tests)."""
    global _feed_cache, _feed_cache_at
    _feed_cache = None
    _feed_cache_at = 0.0


def normalize_for_match(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def extract_article_title_from_query(query: str) -> Optional[str]:
    """
    If the user is asking about a specific article by name, return that title; else None.
    Requires context words (article / substack / post) so we do not misfire on people queries.
    """
    if not query or not query.strip():
        return None
    q = query.strip()
    ql = q.lower()
    if not any(
        w in ql
        for w in (
            "article",
            "substack",
            "roots of all beings",
            "roots of all being",
        )
    ):
        if "post" not in ql and "blog post" not in ql:
            return None

    patterns = [
        # "tell me about Two White Coats, Two Worlds article" (title before the word "article")
        r"(?i)tell me about\s+(.+?)\s+article\s*$",
        r"tell me about this article\s+(?:in brief|briefly)\s+(.+)$",
        r"about this article\s+(?:in brief|briefly)\s+(.+)$",
        r"(?:this|the|that)\s+article\s+(?:in brief|briefly)\s*[:\-]?\s*(.+)$",
        r"(?:read|summary|summarize|summarise)\s+(?:this|the)\s+article\s*[:\-]?\s*(.+)$",
        r"article\s+(?:titled|called|named)\s+[\u201c\u201d\"'](.+?)[\u201c\u201d\"']",
        r"article\s+(?:titled|called|named)\s+(.+?)(?:\?|$)",
    ]
    for pat in patterns:
        m = re.search(pat, q, re.IGNORECASE | re.DOTALL)
        if m:
            t = m.group(1).strip().strip("?").strip()
            if len(t) >= 8:
                return t
    return None


def is_article_by_title_query(query: str) -> bool:
    return extract_article_title_from_query(query) is not None


# RSS intent: explicit title patterns use the same floor as `ranked_feed_matches` in the crawler; implicit
# "tell me about …" uses a higher floor to reduce false positives vs person names.
RESOLVE_EXPLICIT_RSS_MIN_SCORE = 70.0
RESOLVE_IMPLICIT_TELL_ME_RSS_MIN_SCORE = 75.0


def _normalize_query_punctuation_for_intent(q: str) -> str:
    """
    Strip trailing spaces and repeated ? ! . so patterns are not broken by
    "… at prakriti ??" or "… event   ???".
    """
    if not (q and q.strip()):
        return (q or "").strip()
    return re.sub(r"[\s?.!]+$", "", q.strip())


def extract_tell_me_about_tail(query: str) -> Optional[str]:
    """Text after a leading 'tell me about' (e.g. implicit Substack post phrase)."""
    qn = _normalize_query_punctuation_for_intent((query or ""))
    m = re.search(r"(?i)tell\s+me\s+about\s+(.+)$", qn)
    if not m:
        return None
    return m.group(1).strip().rstrip("?.!, ")


def extract_what_is_post_phrase(query: str) -> Optional[str]:
    """
    Phrase for implicit Roots match from definitional questions, e.g.:
    'What is the schoolaroo event at Prakriti?', "What's schoolaroo?".
    """
    q = _normalize_query_punctuation_for_intent((query or ""))
    if not q:
        return None
    patterns = [
        # What is (the) … optional 'at Prakriti' (strip trailing ?! before we run this)
        r"(?i)what\'?s?\s+is\s+(?:the\s+)?(.+?)(?:\s+at\s+prakriti)\s*$",
        r"(?i)what\'?s?\s+is\s+(?:the\s+)?(.+?)\s*$",
        # What's the … ?  (contraction, already includes "is")
        r"(?i)what\'s\s+(?:the\s+)?(.+?)(?:\s+at\s+prakriti)\s*$",
        r"(?i)what\'s\s+(?:the\s+)?(.+?)\s*$",
    ]
    for pat in patterns:
        m = re.search(pat, q)
        if m:
            t = m.group(1).strip().rstrip("?.!, ")
            t = re.sub(r"(?i)\s+at\s+prakriti\s*$", "", t).strip()
            if t:
                return t
    return None


def extract_implicit_roots_post_phrase(query: str) -> Optional[str]:
    """Topic phrase for 'tell me about …' or 'what is …' style Roots/Substack intent."""
    return extract_tell_me_about_tail(query) or extract_what_is_post_phrase(query)


# When the RSS only contains recent items, older /p/ URLs never appear; keep a small
# phrase map aligned with web_crawler_agent article_url_mapping.
KNOWN_TELL_ME_SUBSTACK_INTENT_MAX_SCORE = 100.0


def _known_substack_intent_for_tell_me_tail(
    tail: str,
) -> Optional[Tuple[str, str, float]]:
    n = normalize_for_match(tail)
    if len(n) < 4:
        return None
    w = set(n.split())
    p_student_voice = "https://rootsofallbeings.substack.com/p/student-voice-a-guide-for-shaping"
    p_planet = "https://rootsofallbeings.substack.com/p/can-we-save-the-planet-or-should"
    p_welcome = "https://rootsofallbeings.substack.com/p/welcoming-new-members-to-prakriti"
    p_travel = "https://rootsofallbeings.substack.com/p/a-travelogue-on-our-recent-ole-at"
    p_ole = "https://rootsofallbeings.substack.com/p/outbound-learning-expedition-ole"
    if "student" in w and "voice" in w:
        return (p_student_voice, "Student Voice: A Guide for Shaping", KNOWN_TELL_ME_SUBSTACK_INTENT_MAX_SCORE)
    if "guide" in w and "shaping" in w:
        return (p_student_voice, "Student Voice: A Guide for Shaping", KNOWN_TELL_ME_SUBSTACK_INTENT_MAX_SCORE)
    if ("green" in w and "school" in w) or ("save" in w and "planet" in w):
        return (p_planet, "Can we save the planet or should the planet save itself from us", KNOWN_TELL_ME_SUBSTACK_INTENT_MAX_SCORE)
    if "welcoming" in w and "member" in w:
        return (p_welcome, "Welcoming New Members to Prakriti", KNOWN_TELL_ME_SUBSTACK_INTENT_MAX_SCORE)
    if "travelogue" in w:
        return (p_travel, "A Travelogue on Our Recent OLE at Prakriti", KNOWN_TELL_ME_SUBSTACK_INTENT_MAX_SCORE)
    if "outbound" in w or "ole" in w:
        return (p_ole, "Outbound Learning Expedition (OLE)", KNOWN_TELL_ME_SUBSTACK_INTENT_MAX_SCORE)
    return None


def resolve_roots_substack_intent(
    query: str,
    session: Optional[requests.Session] = None,
    entries: Optional[List[Tuple[str, str]]] = None,
) -> Optional[Tuple[str, str, float]]:
    """
    If the query points at a specific Roots/Substack post, return (url, title_hint, score).

    - If `extract_article_title_from_query` returns a title, match against RSS (min
      RESOLVE_EXPLICIT_RSS_MIN_SCORE). Requires a successful feed read.
    - Else if the query is "tell me about <phrase>" or "what is (the) <phrase> …" (e.g. Schoolaroo),
      match that phrase on RSS, then (if needed) the keyword→/p/ map.
    - `entries` is for tests: pass a list, or pass [] to force RSS-miss and exercise the
      keyword path without network. When `entries` is None, the live feed is fetched.
    """
    if not query or not query.strip():
        return None
    q = _normalize_query_punctuation_for_intent(query.strip())
    feed_entries: Optional[List[Tuple[str, str]]] = entries
    if feed_entries is None:
        try:
            feed_entries = fetch_roots_substack_feed_entries(session)
        except Exception:
            feed_entries = None

    explicit = extract_article_title_from_query(q)
    if explicit:
        if not feed_entries:
            return None
        cands = ranked_feed_matches(
            explicit, feed_entries, min_score=RESOLVE_EXPLICIT_RSS_MIN_SCORE, limit=3
        )
        return cands[0] if cands else None

    tail = extract_implicit_roots_post_phrase(q)
    if not tail or len(tail) < 5:
        return None
    if feed_entries:
        cands = ranked_feed_matches(
            tail, feed_entries, min_score=RESOLVE_IMPLICIT_TELL_ME_RSS_MIN_SCORE, limit=3
        )
        if cands:
            return cands[0]
    return _known_substack_intent_for_tell_me_tail(tail)


def _parse_rss_items(xml_bytes: bytes) -> List[Tuple[str, str]]:
    root = ET.fromstring(xml_bytes)
    out: List[Tuple[str, str]] = []

    def local(tag: str) -> str:
        if not tag:
            return ""
        return tag.rsplit("}", 1)[-1]

    for el in root.iter():
        if local(el.tag) != "item":
            continue
        title_text = ""
        link_text = ""
        for child in el:
            ln = local(child.tag)
            if ln == "title" and (child.text or list(child)):
                title_text = "".join(child.itertext()).strip()
            elif ln == "link" and (child.text is not None or list(child)):
                link_text = (child.text or "").strip() or "".join(child.itertext()).strip()
        if title_text and link_text and link_text.startswith("http"):
            out.append((title_text, link_text))
    return out


def fetch_roots_substack_feed_entries(
    session: Optional[requests.Session] = None,
) -> List[Tuple[str, str]]:
    """
    Return [(post_title, url), ...] from the public RSS feed, with in-process TTL cache.
    """
    global _feed_cache, _feed_cache_at
    now = time.time()
    if _feed_cache is not None and (now - _feed_cache_at) < FEED_TTL_SEC:
        return _feed_cache

    sess = session or requests.Session()
    resp = sess.get(
        ROOTS_SUBSTACK_FEED_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PrakritiChatbot/1.0; +https://prakriti.edu.in)"
        },
    )
    resp.raise_for_status()
    entries = _parse_rss_items(resp.content)
    _feed_cache = entries
    _feed_cache_at = now
    return entries

# Titles in the Roots feed that mention the on-campus / Bookaroo-tied event (post lives on Substack, not prakriti blog-and-news)
_BOOKAROO_SCHOOLAROO_TITLE_SUBSTRINGS = (
    "schoolaroo",
    "bookaroo",
    "literature festival",
    "book camp",
    "festival @ prakriti",
)


def get_substack_post_urls_for_bookaroo_event_context(
    session: Optional[requests.Session] = None,
    entries: Optional[List[Tuple[str, str]]] = None,
    limit: int = 5,
) -> List[str]:
    """
    Return Substack /p/... URLs for feed items whose titles match Schoolaroo, Bookaroo, or
    the literature-festival phrasing. School announcements for this event are usually on
    Substack; call this so the crawler tries those before prakriti.edu.in/blog-and-news.
    """
    if entries is None:
        try:
            entries = fetch_roots_substack_feed_entries(session)
        except Exception:
            return []
    if not entries:
        return []
    out: List[str] = []
    seen = set()
    for title, url in entries:
        if not title or not url or not url.startswith("http"):
            continue
        tl = title.lower()
        if any(s in tl for s in _BOOKAROO_SCHOOLAROO_TITLE_SUBSTRINGS):
            if url not in seen:
                seen.add(url)
                out.append(url)
        if len(out) >= limit:
            break
    return out


def _score_title_against_feed(user_title: str, feed_title: str) -> float:
    nq = normalize_for_match(user_title)
    nt = normalize_for_match(feed_title)
    s1 = _token_set_ratio(nq, nt)
    s2 = _partial_ratio(nq, nt)
    return max(s1, s2)


def best_feed_entry_for_title(
    user_title: str, entries: List[Tuple[str, str]]
) -> Optional[Tuple[str, str, float]]:
    """Return (url, feed_title, score) for the best match, or None if below threshold."""
    if not user_title or not entries:
        return None
    nq = normalize_for_match(user_title)
    if len(nq) < 4:
        return None

    best: Optional[Tuple[str, str, float]] = None
    for feed_title, url in entries:
        s = _score_title_against_feed(user_title, feed_title)
        if best is None or s > best[2]:
            best = (url, feed_title, s)
    if best and best[2] >= MATCH_SCORE_MIN:
        return best
    return None


def ranked_feed_matches(
    user_title: str,
    entries: List[Tuple[str, str]],
    min_score: float = 70.0,
    limit: int = 5,
) -> List[Tuple[str, str, float]]:
    """
    Return up to `limit` (url, feed_title, score) candidates with score >= min_score, best first.
    Used when the top match must be verified against page text.
    """
    if not user_title or not entries:
        return []
    nq = normalize_for_match(user_title)
    if len(nq) < 4:
        return []

    scored: List[Tuple[str, str, float]] = []
    for feed_title, url in entries:
        s = _score_title_against_feed(user_title, feed_title)
        if s >= min_score:
            scored.append((url, feed_title, s))
    scored.sort(key=lambda x: -x[2])
    return scored[:limit]


def content_references_title(
    user_title: str, main_content: str, page_title: str = ""
) -> bool:
    """
    True if fetched body (and optional HTML title) plausibly contains the same article
    the user asked for. Prevents summarizing a different post.
    """
    n = normalize_for_match(user_title)
    blob = normalize_for_match((main_content or "") + " " + (page_title or ""))
    if not n or not blob:
        return False
    if len(n) >= 20 and n in blob:
        return True
    if len(n) >= 20:
        chunk = n[: min(50, len(n))]
        if len(chunk) >= 20 and chunk in blob:
            return True
    words = [w for w in n.split() if len(w) > 3]
    if len(words) < 2:
        return n in blob
    hit = sum(1 for w in words if w in blob)
    need = max(2, int(0.55 * len(words)))
    return hit >= need


def not_found_message_for_title(user_title: str) -> str:
    t = (user_title or "").strip() or "that article"
    return (
        f"[Web] No matching Roots of All Beings (Substack) post was found in the school feed for the title: "
        f"«{t}». Do not invent an article summary. Say the post was not found in the retrieved site data "
        f"and suggest the Roots of All Beings page on prakriti.edu.in or the Substack publication."
    )
