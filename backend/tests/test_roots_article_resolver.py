"""Unit tests for Roots Substack title resolution (no network)."""

from app.utils import roots_article_resolver as rar


MINIMAL_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
<title><![CDATA[Alpha Post Title Here]]></title>
<link>https://rootsofallbeings.substack.com/p/alpha</link>
</item>
<item>
<title>Understanding Our Bodies and Growing Up: A Gentle Conversation</title>
<link>https://rootsofallbeings.substack.com/p/understanding-our-bodies</link>
</item>
</channel></rss>"""


def test_parse_rss_items() -> None:
    items = rar._parse_rss_items(MINIMAL_RSS)
    assert len(items) == 2
    titles = {t for t, _ in items}
    assert "Alpha Post Title Here" in titles
    assert "Understanding Our Bodies and Growing Up: A Gentle Conversation" in titles


def test_extract_article_title() -> None:
    q = (
        "tell me about this article in brief Understanding Our Bodies "
        "and Growing Up: A Gentle Conversation"
    )
    assert (
        rar.extract_article_title_from_query(q)
        == "Understanding Our Bodies and Growing Up: A Gentle Conversation"
    )


def test_extract_title_tell_me_about_x_article() -> None:
    q = "tell me about two white coats , two worlds  article "
    assert rar.extract_article_title_from_query(q) == "two white coats , two worlds"


def test_ranked_feed_matches() -> None:
    entries = rar._parse_rss_items(MINIMAL_RSS)
    m = rar.ranked_feed_matches("Understanding Our Bodies and Growing Up", entries, 70, 3)
    assert m
    assert m[0][0].endswith("understanding-our-bodies")
    assert m[0][2] >= 70.0


def test_content_references_title_accepts() -> None:
    body = "This week we published Understanding Our Bodies and Growing Up: A Gentle Conversation for families."
    assert rar.content_references_title(
        "Understanding Our Bodies and Growing Up: A Gentle Conversation", body, "News"
    )


def test_content_references_title_rejects_wrong_post() -> None:
    body = "Children's Day survey text about the ideal world. Student voice and belonging."
    assert not rar.content_references_title(
        "Understanding Our Bodies and Growing Up: A Gentle Conversation", body, "Other"
    )


def test_not_found_message() -> None:
    s = rar.not_found_message_for_title("Some Missing Title")
    assert "Some Missing Title" in s
    assert "no matching" in s.lower()


def test_get_substack_post_urls_for_bookaroo_event_context() -> None:
    entries = [
        ("Other topic", "https://rootsofallbeings.substack.com/p/other"),
        ("Schoolaroo is Almost Here – Full Programme", "https://rootsofallbeings.substack.com/p/schoolaroo"),
    ]
    urls = rar.get_substack_post_urls_for_bookaroo_event_context(entries=entries, limit=3)
    assert urls == ["https://rootsofallbeings.substack.com/p/schoolaroo"]


def test_resolve_roots_substack_intent_tell_me_about_save_planet() -> None:
    entries = [
        (
            "Can We Save the Planet, or Should the Planet Save Itself—From Us?",
            "https://rootsofallbeings.substack.com/p/can-we-save-the-planet-or-should",
        ),
        ("A Different Post", "https://rootsofallbeings.substack.com/p/other"),
    ]
    q = "tell me about can we save the planet"
    hit = rar.resolve_roots_substack_intent(q, entries=entries)
    assert hit
    assert "can-we-save-the-planet" in hit[0]
    assert "planet" in hit[1].lower()


def test_resolve_roots_substack_intent_tell_me_about_does_not_match_random_person() -> None:
    """Team name should not get a 75+ fuzzy match to unrelated feed titles (offline)."""
    entries = [
        ("Unrelated: Student Voice in the Classroom", "https://rootsofallbeings.substack.com/p/student-voice"),
        ("Weekly update from the garden", "https://rootsofallbeings.substack.com/p/garden"),
    ]
    assert rar.resolve_roots_substack_intent(
        "tell me about Priyanka Oberoi", entries=entries
    ) is None


def test_extract_tell_me_about_tail() -> None:
    assert rar.extract_tell_me_about_tail("Tell me about can we save the planet?") == "can we save the planet"


def test_extract_what_is_schoolaroo_phrase() -> None:
    assert rar.extract_what_is_post_phrase(
        "what is the schoolaroo event at prakriti?"
    ) == "schoolaroo event"
    assert rar.extract_what_is_post_phrase("What is the schoolaroo event?") == "schoolaroo event"
    assert rar.extract_what_is_post_phrase(
        "what is the schoolaroo event at prakriti ??"
    ) == "schoolaroo event"
    assert rar.extract_implicit_roots_post_phrase(
        "what is the schoolaroo event at prakriti?"
    ) == "schoolaroo event"


def test_resolve_what_is_schoolaroo_matches_rss() -> None:
    entries = [
        (
            "Schoolaroo is Almost Here – The Full Programme is Out!",
            "https://rootsofallbeings.substack.com/p/schoolaroo-is-almost-here-the-full",
        ),
    ]
    hit = rar.resolve_roots_substack_intent(
        "what is the schoolaroo event at prakriti?", entries=entries
    )
    assert hit
    assert "schoolaroo-is-almost-here" in hit[0]


def test_resolve_uses_keyword_when_post_not_in_rss_window() -> None:
    """
    Live Substack RSS is short; older posts (e.g. save-the-planet) are often absent.
    Keyword tail map must still return the canonical /p/ URL.
    """
    q = "tell me about can we save planet"
    hit = rar.resolve_roots_substack_intent(q, entries=[])
    assert hit
    assert "can-we-save-the-planet" in hit[0]
    assert hit[2] == 100.0
