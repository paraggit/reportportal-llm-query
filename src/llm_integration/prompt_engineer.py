from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.models.query_models import QueryIntent
from src.utils.config import Config


class PromptEngineer:
    """Construct effective prompts for LLM based on query context."""

    def __init__(self, config: Config):
        self.config = config
        self.prompts = self._load_prompt_templates()

    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load prompt templates from configuration."""
        prompt_file = Path(self.config.paths.prompts_file)

        if prompt_file.exists():
            with open(prompt_file, "r") as f:
                return yaml.safe_load(f)

        # Default prompts if file doesn't exist
        return {
            "system": """You are an intelligent assistant for analyzing software test execution data from Report Portal.
            You help users understand test results, identify patterns, and provide insights about test stability and failures.
            Always be specific and data-driven in your responses.""",
            "test_analysis": """Based on the following test execution data:

            {context}

            User Query: {query}

            Please provide a clear, concise analysis addressing the user's question.
            Include specific test names, failure reasons, and relevant statistics where applicable.""",
            "flaky_analysis": """Analyze the following test execution history to identify flaky tests:

            {context}

            A flaky test is one that has both passed and failed without code changes.

            User Query: {query}

            Identify flaky tests, their failure patterns, and potential causes.""",
            "summary_statistics": """Generate a summary report based on the following test data:

            {summary_stats}

            Recent Test Executions:
            {recent_tests}

            User Query: {query}

            Provide a comprehensive summary with key metrics and insights.""",
        }

    def construct_prompt(
        self, query_intent: QueryIntent, context: str, summary_stats: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Construct appropriate prompt based on query intent."""

        # Select appropriate template
        if query_intent.query_type.value == "flaky_analysis":
            template = self.prompts["flaky_analysis"]
        elif query_intent.query_type.value == "statistics":
            template = self.prompts["summary_statistics"]
        else:
            template = self.prompts["test_analysis"]

        # Build the prompt
        user_prompt = template.format(
            context=context,
            query=query_intent.original_query,
            summary_stats=self._format_summary_stats(summary_stats) if summary_stats else "",
            recent_tests=context,
        )

        return {"system": self.prompts["system"], "user": user_prompt}

    def _format_summary_stats(self, stats: Dict[str, Any]) -> str:
        """Format summary statistics for prompt."""
        if not stats:
            return "No summary statistics available."

        formatted = []
        formatted.append(f"Total Executions: {stats.get('total_executions', 0)}")
        formatted.append(f"Unique Tests: {stats.get('unique_tests', 0)}")
        formatted.append(f"Overall Failure Rate: {stats.get('failure_rate', 0):.2f}%")

        if "status_distribution" in stats:
            formatted.append("\nStatus Distribution:")
            for status, count in stats["status_distribution"].items():
                formatted.append(f"  - {status}: {count}")

        if "platform_distribution" in stats:
            formatted.append("\nPlatform Distribution:")
            for platform, count in stats["platform_distribution"].items():
                formatted.append(f"  - {platform}: {count}")

        if "flaky_tests" in stats and stats["flaky_tests"]:
            formatted.append(f"\nFlaky Tests Detected: {len(stats['flaky_tests'])}")
            formatted.append("Top Flaky Tests:")
            for test in stats["flaky_tests"][:5]:
                formatted.append(f"  - {test}")

        return "\n".join(formatted)

    def create_few_shot_examples(self) -> List[Dict[str, str]]:
        """Create few-shot examples for better query understanding."""
        return [
            {
                "query": "Show me all tests that failed on AWS in the last 7 days",
                "response": "I'll analyze the test failures on AWS platform from the last 7 days...",
            },
            {
                "query": "Which tests are flaky?",
                "response": "I'll identify tests that show inconsistent pass/fail behavior...",
            },
            {
                "query": "Who owns test_storage_basic?",
                "response": "Let me look up the ownership information for test_storage_basic...",
            },
        ]
