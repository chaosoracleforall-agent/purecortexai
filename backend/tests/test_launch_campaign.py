from src.services.launch_campaign import (
    get_launch_prompt_for_day,
    get_all_launch_prompts,
    get_missed_prompts,
    LAUNCH_COUNTDOWN_PROMPTS,
)


def test_get_launch_prompt_for_day_returns_correct_prompt():
    prompt = get_launch_prompt_for_day(9)
    assert prompt is not None
    assert prompt["topic"] == "What is PURECORTEX?"
    assert prompt["content_type"] == "thread"


def test_get_launch_prompt_for_day_returns_none_for_invalid_day():
    assert get_launch_prompt_for_day(99) is None


def test_get_launch_prompt_for_day_catchup_returns_latest():
    """Post-TGE days beyond defined content should catch-up to latest available."""
    prompt = get_launch_prompt_for_day(-5)
    assert prompt is not None
    assert prompt["day_offset"] == 5  # Returns Day +5 content


def test_get_missed_prompts_returns_unposted():
    missed = get_missed_prompts(-3, posted_offsets={0})
    assert len(missed) >= 1
    assert all(p["day_offset"] != 0 for p in missed)  # Day 0 was posted
    assert any(p["day_offset"] == 1 for p in missed)   # Day 1 still missed


def test_get_missed_prompts_returns_empty_before_tge():
    missed = get_missed_prompts(5)
    assert missed == []


def test_get_missed_prompts_all_posted():
    all_offsets = {p["day_offset"] for p in LAUNCH_COUNTDOWN_PROMPTS if p["day_offset"] >= 0}
    missed = get_missed_prompts(-10, posted_offsets=all_offsets)
    assert missed == []


def test_get_launch_prompt_for_tge_day():
    prompt = get_launch_prompt_for_day(0)
    assert prompt is not None
    assert prompt["day_offset"] == 0
    assert "LAUNCH" in prompt["topic"].upper() or "live" in prompt["topic"].lower()


def test_get_launch_prompt_for_day_after_tge():
    prompt = get_launch_prompt_for_day(-1)
    assert prompt is not None
    assert prompt["day_offset"] == 1


def test_all_prompts_have_required_fields():
    for prompt in LAUNCH_COUNTDOWN_PROMPTS:
        assert "day_offset" in prompt
        assert "content_type" in prompt
        assert "topic" in prompt
        assert "seed" in prompt
        assert isinstance(prompt["seed"], str)
        assert len(prompt["seed"]) > 20


def test_all_prompts_sorted_chronologically():
    prompts = get_all_launch_prompts()
    offsets = [p["day_offset"] for p in prompts]
    assert offsets == sorted(offsets)


def test_no_duplicate_day_offsets():
    offsets = [p["day_offset"] for p in LAUNCH_COUNTDOWN_PROMPTS]
    assert len(offsets) == len(set(offsets))


def test_content_types_are_valid():
    valid_types = {
        "protocol_update",
        "tokenomics_education",
        "governance_highlight",
        "agent_ecosystem",
        "community_engagement",
        "metrics_report",
        "thread",
    }
    for prompt in LAUNCH_COUNTDOWN_PROMPTS:
        assert prompt["content_type"] in valid_types, (
            f"Invalid content_type '{prompt['content_type']}' for day {prompt['day_offset']}"
        )
