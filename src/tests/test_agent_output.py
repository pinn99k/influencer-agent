"""Unit tests for AgentOutput.from_raw (V2 Spiral 5-A). Pure ASCII, no I/O."""
import json

from agents.agent_output import AgentOutput, _DELIM_START, _DELIM_END


def _block(payload: dict) -> str:
    return f"# Title\n\nbody content\n\n{_DELIM_START}\n{json.dumps(payload)}\n{_DELIM_END}"


class TestFromRaw:
    def test_full_json_block(self):
        raw = _block({
            "questions": ["q1", "q2"],
            "comments": ["c1"],
            "confidence": 0.75,
            "metadata": {"key": "val"},
        })
        out = AgentOutput.from_raw(raw)
        assert out.content == "# Title\n\nbody content"
        assert out.questions == ["q1", "q2"]
        assert out.comments == ["c1"]
        assert out.confidence == 0.75
        assert out.metadata == {"key": "val"}

    def test_no_block_backward_compat(self):
        raw = "## plain markdown output\n\nsome analysis here"
        out = AgentOutput.from_raw(raw)
        assert out.content == "## plain markdown output\n\nsome analysis here"
        assert out.questions == []
        assert out.comments == []
        assert out.confidence == 1.0
        assert out.metadata == {}

    def test_broken_json(self):
        raw = f"body text\n\n{_DELIM_START}\n{{not valid json,,,}}\n{_DELIM_END}"
        out = AgentOutput.from_raw(raw)
        # whole text minus delimiters becomes content; no exception
        assert "body text" in out.content
        assert _DELIM_START not in out.content
        assert _DELIM_END not in out.content
        assert out.questions == []
        assert out.confidence == 1.0

    def test_partial_keys(self):
        raw = _block({"questions": ["only q"]})
        out = AgentOutput.from_raw(raw)
        assert out.questions == ["only q"]
        assert out.comments == []
        assert out.confidence == 1.0
        assert out.metadata == {}

    def test_confidence_clip_high(self):
        out = AgentOutput.from_raw(_block({"confidence": 1.5}))
        assert out.confidence == 1.0

    def test_confidence_clip_low(self):
        out = AgentOutput.from_raw(_block({"confidence": -0.5}))
        assert out.confidence == 0.0

    def test_confidence_non_numeric(self):
        out = AgentOutput.from_raw(_block({"confidence": "high"}))
        assert out.confidence == 1.0

    def test_confidence_bool_rejected(self):
        out = AgentOutput.from_raw(_block({"confidence": True}))
        assert out.confidence == 1.0

    def test_empty_string_questions_filtered(self):
        out = AgentOutput.from_raw(_block({"questions": ["", "  ", "real question"]}))
        assert out.questions == ["real question"]

    def test_start_delim_no_end(self):
        raw = f"content before\n\n{_DELIM_START}\n{json.dumps({'confidence': 0.5})}"
        out = AgentOutput.from_raw(raw)
        assert out.content == "content before"
        assert out.confidence == 0.5

    def test_questions_null(self):
        out = AgentOutput.from_raw(_block({"questions": None, "comments": None}))
        assert out.questions == []
        assert out.comments == []

    def test_empty_and_none_input(self):
        assert AgentOutput.from_raw("").content == ""
        assert AgentOutput.from_raw(None).content == ""

    def test_metadata_non_dict_ignored(self):
        out = AgentOutput.from_raw(_block({"metadata": ["not", "a", "dict"]}))
        assert out.metadata == {}
