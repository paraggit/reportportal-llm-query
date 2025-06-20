from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from ..models.test_execution import Launch, TestExecution


class DataNormalizer:
    """Normalize Report Portal data for LLM consumption."""

    @staticmethod
    def normalize_test_executions(test_executions: List[TestExecution]) -> pd.DataFrame:
        """Convert test executions to pandas DataFrame."""
        data = []

        for test in test_executions:
            data.append(
                {
                    "test_id": test.id,
                    "test_name": test.name,
                    "status": test.status,
                    "start_time": datetime.fromtimestamp(test.startTime / 1000),
                    "end_time": (
                        datetime.fromtimestamp(test.endTime / 1000) if test.endTime else None
                    ),
                    "duration_seconds": (
                        (test.endTime - test.startTime) / 1000 if test.endTime else None
                    ),
                    "platform": test.attributes.get("platform", "unknown"),
                    "owner": test.attributes.get("owner", "unknown"),
                    "error_message": test.issue.comment if test.issue else None,
                    "tags": ",".join(test.tags) if test.tags else "",
                    "launch_id": test.launchId,
                    "parent_id": test.parentId,
                }
            )

        return pd.DataFrame(data)

    @staticmethod
    def create_test_summary(df: pd.DataFrame) -> Dict[str, Any]:
        """Create summary statistics from test data."""
        if df.empty:
            return {}

        summary = {
            "total_executions": len(df),
            "unique_tests": df["test_name"].nunique(),
            "status_distribution": df["status"].value_counts().to_dict(),
            "platform_distribution": df["platform"].value_counts().to_dict(),
            "average_duration": df["duration_seconds"].mean(),
            "failure_rate": (df["status"] == "FAILED").mean() * 100,
            "date_range": {
                "start": df["start_time"].min().isoformat() if not df.empty else None,
                "end": df["start_time"].max().isoformat() if not df.empty else None,
            },
        }

        # Identify flaky tests
        test_status_counts = df.groupby("test_name")["status"].value_counts().unstack(fill_value=0)
        flaky_tests = test_status_counts[
            (test_status_counts.get("PASSED", 0) > 0) & (test_status_counts.get("FAILED", 0) > 0)
        ].index.tolist()

        summary["flaky_tests"] = flaky_tests[:10]  # Top 10 flaky tests

        return summary

    @staticmethod
    def format_for_llm(df: pd.DataFrame, max_rows: int = 50) -> str:
        """Format DataFrame for LLM context."""
        if df.empty:
            return "No test data available."

        # Select most relevant columns
        columns = ["test_name", "status", "start_time", "platform", "owner", "error_message"]
        df_subset = df[columns].head(max_rows)

        # Convert to string representation
        return df_subset.to_string(index=False, max_rows=max_rows)
