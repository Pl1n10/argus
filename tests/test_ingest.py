import pytest

from argus.ingest import ParseError, parse


class TestGeneric:
    def test_bare_body_is_success(self):
        p = parse("generic", {})
        assert p.status == "success"
        assert p.exit_code == 0

    def test_none_body_is_success(self):
        assert parse("generic", None).status == "success"

    def test_nonzero_exit_is_fail(self):
        p = parse("generic", {"exit_code": 1})
        assert p.status == "fail"
        assert p.exit_code == 1

    def test_carries_metrics(self):
        p = parse("generic", {"exit_code": 0, "bytes": 1234, "duration_s": 5.5,
                              "log_tail": "done"})
        assert (p.bytes, p.duration_s, p.log_tail) == (1234, 5.5, "done")

    def test_exit_code_from_string(self):
        assert parse("generic", {"exit_code": "2"}).status == "fail"

    def test_bad_exit_code_raises(self):
        with pytest.raises(ParseError):
            parse("generic", {"exit_code": "boom"})


class TestRestic:
    def test_summary_success(self):
        p = parse("restic", {"message_type": "summary",
                            "total_bytes_processed": 5000, "total_duration": 12.0})
        assert p.status == "success"
        assert p.bytes == 5000
        assert p.duration_s == 12.0

    def test_summary_without_message_type(self):
        p = parse("restic", {"total_bytes_processed": 42})
        assert p.status == "success" and p.bytes == 42

    def test_error_is_fail(self):
        p = parse("restic", {"message_type": "error", "error": "repo locked"})
        assert p.status == "fail"
        assert "locked" in p.log_tail

    def test_not_a_summary_raises(self):
        with pytest.raises(ParseError):
            parse("restic", {"message_type": "status", "percent_done": 0.5})


class TestBorg:
    def test_archive_stats(self):
        p = parse("borg", {"archive": {"stats": {"original_size": 9000}, "duration": 7.5}})
        assert p.status == "success"
        assert p.bytes == 9000
        assert p.duration_s == 7.5

    def test_missing_archive_raises(self):
        with pytest.raises(ParseError):
            parse("borg", {"repository": {}})


def test_unknown_flavor_raises():
    with pytest.raises(ParseError):
        parse("kopia", {})
