import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


class URLValidator:
    """Validate and normalize URLs."""

    @staticmethod
    def validate_url(url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL by ensuring proper format."""
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        # Remove trailing slash
        return url.rstrip("/")


class QueryValidator:
    """Validate user queries."""

    MAX_QUERY_LENGTH = 1000
    MIN_QUERY_LENGTH = 3

    @staticmethod
    def validate_query(query: str) -> Tuple[bool, Optional[str]]:
        """Validate user query and return (is_valid, error_message)"""
        if not query or not query.strip():
            return False, "Query cannot be empty"

        query = query.strip()

        if len(query) < QueryValidator.MIN_QUERY_LENGTH:
            return (
                False,
                f"Query too short. Minimum {QueryValidator.MIN_QUERY_LENGTH} characters required",
            )

        if len(query) > QueryValidator.MAX_QUERY_LENGTH:
            return (
                False,
                f"Query too long. Maximum {QueryValidator.MAX_QUERY_LENGTH} characters allowed",
            )

        # Check for potential injection attempts
        dangerous_patterns = [
            r"<script",
            r"javascript:",
            r"exec\s*\(",
            r"eval\s*\(",
            r"__import__",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "Query contains potentially unsafe content"

        return True, None
