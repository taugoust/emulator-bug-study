import json
from io import StringIO
from buglib.jsonl import write_jsonl


class TestWriteJsonl:
    def test_single_record(self):
        buf = StringIO()
        write_jsonl({"id": 1, "title": "bug"}, buf)
        line = buf.getvalue()
        assert line.endswith("\n")
        parsed = json.loads(line)
        assert parsed == {"id": 1, "title": "bug"}

    def test_multiple_records(self):
        buf = StringIO()
        write_jsonl({"id": 1}, buf)
        write_jsonl({"id": 2}, buf)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == 1
        assert json.loads(lines[1])["id"] == 2

    def test_unicode(self):
        buf = StringIO()
        write_jsonl({"title": "ü日本語"}, buf)
        parsed = json.loads(buf.getvalue())
        assert parsed["title"] == "ü日本語"

    def test_nested_structure(self):
        buf = StringIO()
        record = {"id": 42, "labels": ["bug", "critical"], "meta": {"state": "open"}}
        write_jsonl(record, buf)
        parsed = json.loads(buf.getvalue())
        assert parsed["labels"] == ["bug", "critical"]
        assert parsed["meta"]["state"] == "open"

    def test_none_values(self):
        buf = StringIO()
        write_jsonl({"id": 1, "description": None}, buf)
        parsed = json.loads(buf.getvalue())
        assert parsed["description"] is None
