from datetime import datetime, timedelta

import pytest

from src.utils.validators import (
    DateTimeValidator,
    PlatformValidator,
    QueryValidator,
    StatusValidator,
    TestNameValidator,
    URLValidator,
    sanitize_string,
)


class TestURLValidator:
    def test_valid_urls(self):
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "http://localhost:8080",
            "https://sub.domain.com/path",
        ]

        for url in valid_urls:
            assert URLValidator.validate_url(url) is True

    def test_invalid_urls(self):
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Not http/https
            "",
            "http://",
        ]

        for url in invalid_urls:
            assert URLValidator.validate_url(url) is False

    def test_normalize_url(self):
        assert URLValidator.normalize_url("example.com") == "http://example.com"
        assert URLValidator.normalize_url("http://example.com/") == "http://example.com"


class TestQueryValidator:
    def test_valid_queries(self):
        valid_queries = [
            "Show me failed tests",
            "Which tests are flaky?",
            "What is the test failure rate on AWS?",
        ]

        for query in valid_queries:
            is_valid, error = QueryValidator.validate_query(query)
            assert is_valid is True
            assert error is None

    def test_invalid_queries(self):
        # Empty query
        is_valid, error = QueryValidator.validate_query("")
        assert is_valid is False
        assert "empty" in error

        # Too short
        is_valid, error = QueryValidator.validate_query("a")
        assert is_valid is False
        assert "short" in error

        # Too long
        is_valid, error = QueryValidator.validate_query("x" * 1001)
        assert is_valid is False
        assert "long" in error


class TestDateTimeValidator:
    def test_parse_standard_formats(self):
        test_cases = [
            ("2024-01-15", datetime(2024, 1, 15)),
            ("15/01/2024", datetime(2024, 1, 15)),
            ("15-01-2024", datetime(2024, 1, 15)),
        ]

        for date_str, expected in test_cases:
            result = DateTimeValidator.parse_datetime(date_str)
            assert result.date() == expected.date()

    def test_parse_relative_dates(self):
        # Test "today"
        result = DateTimeValidator.parse_datetime("today")
        assert result.date() == datetime.now().date()

        # Test "yesterday"
        result = DateTimeValidator.parse_datetime("yesterday")
        expected = datetime.now().date() - timedelta(days=1)
        assert result.date() == expected


class TestPlatformValidator:
    def test_normalize_platform(self):
        assert PlatformValidator.normalize_platform("AWS") == "aws"
        assert PlatformValidator.normalize_platform("amazon") == "aws"
        assert PlatformValidator.normalize_platform("GCP") == "gcp"
        assert PlatformValidator.normalize_platform("google") == "gcp"
        assert PlatformValidator.normalize_platform("invalid") is None

    def test_is_valid_platform(self):
        assert PlatformValidator.is_valid_platform("aws") is True
        assert PlatformValidator.is_valid_platform("Azure") is True
        assert PlatformValidator.is_valid_platform("invalid-platform") is False


class TestStatusValidator:
    def test_normalize_status(self):
        assert StatusValidator.normalize_status("passed") == "PASSED"
        assert StatusValidator.normalize_status("fail") == "FAILED"
        assert StatusValidator.normalize_status("green") == "PASSED"
        assert StatusValidator.normalize_status("red") == "FAILED"
        assert StatusValidator.normalize_status("invalid") is None


class TestSanitizeString:
    def test_sanitize_normal_string(self):
        assert sanitize_string("Hello World") == "Hello World"

    def test_sanitize_with_control_chars(self):
        text_with_control = "Hello\x00World\x01"
        assert sanitize_string(text_with_control) == "HelloWorld"

    def test_sanitize_long_string(self):
        long_text = "x" * 2000
        result = sanitize_string(long_text, max_length=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")
