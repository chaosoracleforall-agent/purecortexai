from src.services.engagement_scheduler import (
    CYCLE_MAX_FOLLOWS,
    CYCLE_MAX_LIKES,
    CYCLE_MAX_MENTION_REPLIES,
    CYCLE_MAX_QUOTE_TWEETS,
    CYCLE_MAX_REPLIES,
    CYCLE_MAX_RETWEETS,
    OPERATION_SCHEDULE,
    EngagementScheduler,
)


def test_advance_cycle_increments():
    scheduler = EngagementScheduler()
    assert scheduler.cycle == 0
    assert scheduler.advance_cycle() == 1
    assert scheduler.advance_cycle() == 2
    assert scheduler.cycle == 2


def test_should_run_mentions_every_cycle():
    scheduler = EngagementScheduler()
    for _ in range(10):
        scheduler.advance_cycle()
        assert scheduler.should_run("mentions") is True


def test_should_run_home_timeline_every_other_cycle():
    scheduler = EngagementScheduler()
    results = []
    for _ in range(8):
        scheduler.advance_cycle()
        results.append(scheduler.should_run("home_timeline"))
    assert results == [False, True, False, True, False, True, False, True]


def test_should_run_conversation_threads_every_third():
    scheduler = EngagementScheduler()
    results = []
    for _ in range(9):
        scheduler.advance_cycle()
        results.append(scheduler.should_run("conversation_threads"))
    assert results == [False, False, True, False, False, True, False, False, True]


def test_should_run_campaign_targets_every_fourth():
    scheduler = EngagementScheduler()
    results = []
    for _ in range(8):
        scheduler.advance_cycle()
        results.append(scheduler.should_run("campaign_targets"))
    assert results == [False, False, False, True, False, False, False, True]


def test_should_run_dynamic_discovery_every_eighth():
    scheduler = EngagementScheduler()
    results = []
    for _ in range(16):
        scheduler.advance_cycle()
        results.append(scheduler.should_run("dynamic_discovery"))
    true_indices = [i for i, v in enumerate(results) if v]
    assert true_indices == [7, 15]


def test_should_run_unknown_operation_defaults_to_every_cycle():
    scheduler = EngagementScheduler()
    scheduler.advance_cycle()
    assert scheduler.should_run("nonexistent_op") is True


def test_get_cycle_caps_returns_expected_keys():
    caps = EngagementScheduler.get_cycle_caps()
    assert set(caps.keys()) == {
        "replies",
        "retweets",
        "likes",
        "quote_tweets",
        "follows",
        "mention_replies",
    }


def test_get_cycle_caps_values_match_module_constants():
    caps = EngagementScheduler.get_cycle_caps()
    assert caps["replies"] == CYCLE_MAX_REPLIES
    assert caps["retweets"] == CYCLE_MAX_RETWEETS
    assert caps["likes"] == CYCLE_MAX_LIKES
    assert caps["quote_tweets"] == CYCLE_MAX_QUOTE_TWEETS
    assert caps["follows"] == CYCLE_MAX_FOLLOWS
    assert caps["mention_replies"] == CYCLE_MAX_MENTION_REPLIES


def test_operation_schedule_has_required_operations():
    required = {"mentions", "search", "home_timeline", "conversation_threads", "campaign_targets", "dynamic_discovery"}
    assert required.issubset(set(OPERATION_SCHEDULE.keys()))


def test_operation_schedule_mentions_runs_most_frequently():
    assert OPERATION_SCHEDULE["mentions"] == 1
    for op, interval in OPERATION_SCHEDULE.items():
        assert interval >= OPERATION_SCHEDULE["mentions"]
