from src.services.social_campaign import (
    SEARCH_QUERIES,
    get_search_queries,
    get_search_queries_for_cycle,
    _CORE_QUERY_COUNT,
)
from src.agents.social_agent import SocialAgent


def test_search_queries_expanded():
    """Verify the expanded query list has more than the original 10."""
    assert len(SEARCH_QUERIES) >= 19


def test_search_queries_core_always_included():
    """Core queries should appear in every rotated subset."""
    core = SEARCH_QUERIES[:_CORE_QUERY_COUNT]
    for _ in range(20):
        subset = get_search_queries_for_cycle(max_queries=6)
        for q in core:
            assert q in subset, f"Core query missing: {q}"


def test_search_query_rotation_varies():
    """Different cycles should produce different query subsets."""
    subsets = set()
    for _ in range(20):
        subset = tuple(get_search_queries_for_cycle(max_queries=6))
        subsets.add(subset)
    # With 7 rotating queries and rotation step of 2, we should see variation
    assert len(subsets) > 1


def test_search_query_rotation_respects_max():
    """Rotated subset should never exceed max_queries."""
    for _ in range(20):
        subset = get_search_queries_for_cycle(max_queries=4)
        assert len(subset) <= 4


def test_search_query_rotation_covers_all_queries():
    """Over enough cycles, all queries should appear at least once."""
    seen = set()
    for _ in range(50):
        subset = get_search_queries_for_cycle(max_queries=6)
        seen.update(subset)
    assert seen == set(SEARCH_QUERIES)


def test_get_search_queries_returns_all():
    """The non-rotating version should return every query."""
    assert get_search_queries() == SEARCH_QUERIES


def test_no_retweet_filter_in_all_queries():
    """All queries should filter out retweets."""
    for query in SEARCH_QUERIES:
        assert "-is:retweet" in query


# --- Mention intent classification tests ---

def test_classify_mention_intent_question():
    assert SocialAgent._classify_mention_intent("What is PURECORTEX?") == "question"
    assert SocialAgent._classify_mention_intent("@purecortexai how does governance work?") == "question"


def test_classify_mention_intent_positive():
    assert SocialAgent._classify_mention_intent("@purecortexai this is amazing!") == "positive_sentiment"
    assert SocialAgent._classify_mention_intent("Love what you're building!") == "positive_sentiment"


def test_classify_mention_intent_newcomer():
    assert SocialAgent._classify_mention_intent("Just found @purecortexai, looks cool") == "newcomer"
    assert SocialAgent._classify_mention_intent("I'm new to this project") == "newcomer"


def test_classify_mention_intent_general():
    assert SocialAgent._classify_mention_intent("@purecortexai launched on Algorand") == "general"


# --- Ecosystem relevance tests ---

def test_is_ecosystem_relevant_positive():
    assert SocialAgent._is_ecosystem_relevant("Algorand developer building DeFi tools") is True
    assert SocialAgent._is_ecosystem_relevant("AI agent researcher and blockchain builder") is True


def test_is_ecosystem_relevant_negative():
    assert SocialAgent._is_ecosystem_relevant("I like cooking and travel") is False
    assert SocialAgent._is_ecosystem_relevant("") is False
