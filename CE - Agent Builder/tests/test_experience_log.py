"""Tests for experience log — uses DuckDB fixture."""

from csuite.learning.experience_log import ExperienceLog


class TestDetectCorrection:
    """Static method — no DB needed."""

    def test_detects_actually(self):
        assert ExperienceLog.detect_correction("No, actually use React instead")

    def test_detects_wrong(self):
        assert ExperienceLog.detect_correction("That's wrong, try again")

    def test_detects_dont_recommend(self):
        assert ExperienceLog.detect_correction("Don't recommend Canva")

    def test_detects_incorrect(self):
        assert ExperienceLog.detect_correction("That's incorrect")

    def test_detects_never_use(self):
        assert ExperienceLog.detect_correction("Never use that framework")

    def test_no_match(self):
        assert not ExperienceLog.detect_correction("Sounds good, let's proceed")

    def test_case_insensitive(self):
        assert ExperienceLog.detect_correction("THAT'S WRONG")


class TestExperienceLogDB:
    def test_add_and_get_lessons(self, duckdb_store):
        log = ExperienceLog()
        log.add_lesson("cfo", "Always check margins first")
        log.add_lesson("cfo", "Use DCF for valuations")
        result = log.get_lessons("cfo", limit=10)
        assert "Always check margins first" in result
        assert "Use DCF for valuations" in result

    def test_get_lessons_empty(self, duckdb_store):
        log = ExperienceLog()
        result = log.get_lessons("ceo", limit=10)
        assert result == ""

    def test_lessons_separated_by_role(self, duckdb_store):
        log = ExperienceLog()
        log.add_lesson("cfo", "CFO lesson")
        log.add_lesson("cto", "CTO lesson")
        cfo_result = log.get_lessons("cfo")
        assert "CFO lesson" in cfo_result
        assert "CTO lesson" not in cfo_result
