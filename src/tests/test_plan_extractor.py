from core.plan_extractor import extract_plan, extract_weeks


def test_extract_weeks_regular_format():
    text = (
        "#### Week 1\n"
        "- reel one\n"
        "1. post one\n"
        "\n#### Week 2\n"
        "* live one\n"
        "\n#### Week 3\n"
        "- guide one\n"
        "\n#### Week 4\n"
        "- review one\n"
    )

    weeks = extract_weeks(text)

    assert len(weeks) == 4
    assert weeks[0] == {"num": 1, "items": ["reel one", "post one"]}
    assert weeks[1] == {"num": 2, "items": ["live one"]}
    assert weeks[2] == {"num": 3, "items": ["guide one"]}
    assert weeks[3] == {"num": 4, "items": ["review one"]}


def test_extract_weeks_missing_week_returns_empty_items():
    weeks = extract_weeks("#### Week 1\n- item\n\n#### Week 3\n- later")

    assert weeks[0]["items"] == ["item"]
    assert weeks[1] == {"num": 2, "items": []}
    assert weeks[2]["items"] == ["later"]
    assert weeks[3] == {"num": 4, "items": []}


def test_extract_plan_next_actions_and_kpi():
    report = (
        "## \uc9c0\uae08 \ub2f9\uc7a5 \ud560 3\uac00\uc9c0\n"
        "1. first action\n"
        "2. second action\n"
        "3. third action\n"
        "\n## \uc131\uacf5 \uc9c0\ud45c (30\uc77c)\n"
        "- followers: 300\n"
        "- content: 12\n"
    )

    plan = extract_plan(final_report=report)

    assert plan["next_actions"] == ["first action", "second action", "third action"]
    assert plan["kpi"] == ["followers: 300", "content: 12"]


def test_extract_plan_kpi_header_without_days():
    report = "## \uc131\uacf5 \uc9c0\ud45c\n- views: 10000\n"

    plan = extract_plan(final_report=report)

    assert plan["kpi"] == ["views: 10000"]


def test_extract_plan_empty_input():
    plan = extract_plan()

    assert plan == {
        "weeks": [
            {"num": 1, "items": []},
            {"num": 2, "items": []},
            {"num": 3, "items": []},
            {"num": 4, "items": []},
        ],
        "next_actions": [],
        "kpi": [],
    }


def test_extract_plan_combined_weeks_and_report():
    """`extract_plan` with both concept_output and final_report returns all three keys."""
    concept = (
        "#### Week 1\n- reel post\n"
        "\n#### Week 2\n1. live stream\n"
        "\n#### Week 3\n* tutorial video\n"
        "\n#### Week 4\n- monthly review\n"
    )
    # headers use unicode escapes to avoid CJK code-point contamination
    report = (
        "## \uc9c0\uae08 \ub2f9\uc7a5 \ud560 3\uac00\uc9c0\n"
        "1. setup profile\n"
        "2. shoot first reel\n"
        "3. hashtag research\n\n"
        "## \uc131\uacf5 \uc9c0\ud45c (30\uc77c)\n"
        "- followers 300\n"
        "- posts 12\n"
    )

    plan = extract_plan(concept_output=concept, final_report=report)

    assert len(plan["weeks"]) == 4
    assert plan["weeks"][0] == {"num": 1, "items": ["reel post"]}
    assert plan["weeks"][1] == {"num": 2, "items": ["live stream"]}
    assert plan["weeks"][2] == {"num": 3, "items": ["tutorial video"]}
    assert plan["weeks"][3] == {"num": 4, "items": ["monthly review"]}
    assert plan["next_actions"] == ["setup profile", "shoot first reel", "hashtag research"]
    assert plan["kpi"] == ["followers 300", "posts 12"]


def test_extract_weeks_asterisk_markers():
    """Asterisk (*) list markers are parsed the same as dash and numbered."""
    text = (
        "#### Week 1\n"
        "* item alpha\n"
        "* item beta\n"
        "\n#### Week 2\n"
        "* item gamma\n"
    )

    weeks = extract_weeks(text)

    assert weeks[0]["items"] == ["item alpha", "item beta"]
    assert weeks[1]["items"] == ["item gamma"]
    assert weeks[2] == {"num": 3, "items": []}
    assert weeks[3] == {"num": 4, "items": []}


def test_extract_plan_next_actions_only():
    """Only next_actions section present -- kpi returns empty list."""
    report = (
        "## \uc9c0\uae08 \ub2f9\uc7a5 \ud560 3\uac00\uc9c0\n"
        "1. action one\n"
        "2. action two\n"
    )

    plan = extract_plan(final_report=report)

    assert plan["next_actions"] == ["action one", "action two"]
    assert plan["kpi"] == []


def test_extract_plan_kpi_only():
    """Only kpi section present -- next_actions returns empty list."""
    report = "## \uc131\uacf5 \uc9c0\ud45c\n- metric a\n- metric b\n"

    plan = extract_plan(final_report=report)

    assert plan["next_actions"] == []
    assert plan["kpi"] == ["metric a", "metric b"]
