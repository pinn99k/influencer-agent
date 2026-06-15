"""Unit tests for deterministic subscriber-count parsing.

All Korean characters are written as unicode escapes to guarantee correct
codepoints (see .claude/lessons.md rule 1).
"""
from unittest.mock import patch

from agents.competition_analyst import (
    CompetitionAnalystAgent,
    _parse_subscriber_count,
)

_MAN = "만"      # man (10^4)
_CHEON = "천"    # cheon (10^3)
_EOK = "억"      # eok (10^8)
_MYEONG = "명"   # myeong (counter)


def test_parse_man():
    assert _parse_subscriber_count("2.13" + _MAN) == 21300
    assert _parse_subscriber_count("구독자 5" + _MAN) == 50000  # subscribers 5 man


def test_parse_cheon():
    assert _parse_subscriber_count("3" + _CHEON) == 3000


def test_parse_eok():
    assert _parse_subscriber_count("0.5" + _EOK) == 50000000


def test_parse_k_and_m():
    assert _parse_subscriber_count("1.5K subscribers") == 1500
    assert _parse_subscriber_count("3M") == 3000000
    assert _parse_subscriber_count("250K") == 250000


def test_parse_plain_with_commas():
    assert _parse_subscriber_count("12,300" + _MYEONG) == 12300
    assert _parse_subscriber_count("45,000 subscribers") == 45000


def test_parse_none_when_absent():
    assert _parse_subscriber_count("no number here") is None
    assert _parse_subscriber_count("") is None
    assert _parse_subscriber_count(None) is None


def test_man_takes_precedence_over_plain():
    # '2.13만' should resolve via the man unit, not the bare digits.
    assert _parse_subscriber_count("2.13" + _MAN + " (213)") == 21300


def _fake_search_with_counts(query):
    return [
        {
            "title": "Creator A - YouTube",
            "link": f"http://x/{query}/a",
            "snippet": "구독자 2.13" + _MAN,  # subscribers 2.13 man
        },
        {
            "title": "Creator B 1.5K",
            "link": f"http://x/{query}/b",
            "snippet": "no count in snippet",
        },
    ]


def test_collect_search_results_attaches_parsed_count():
    agent = CompetitionAnalystAgent()
    with patch(
        "agents.competition_analyst.serper_client.search",
        side_effect=_fake_search_with_counts,
    ):
        results = agent._collect_search_results(["q1"])
    by_link = {r["link"]: r for r in results}
    a = by_link["http://x/q1/a"]
    b = by_link["http://x/q1/b"]
    assert a["_subscriber_parsed"] == 21300       # from snippet
    assert b["_subscriber_parsed"] == 1500        # fell back to title '1.5K'


def test_collect_dedupes_by_link():
    agent = CompetitionAnalystAgent()
    with patch(
        "agents.competition_analyst.serper_client.search",
        side_effect=_fake_search_with_counts,
    ):
        results = agent._collect_search_results(["q1", "q1"])
    links = [r["link"] for r in results]
    assert len(links) == len(set(links))
