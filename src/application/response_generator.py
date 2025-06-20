import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from loguru import logger
from pydantic import BaseModel

from ..data_access.cache_manager import CacheManager
from ..data_access.data_normalizer import DataNormalizer
from ..data_access.reportportal_client import ReportPortalClient
from ..llm_integration.llm_interface import LLMInterface
from ..llm_integration.prompt_engineer import PromptEngineer
from ..llm_integration.query_processor import QueryProcessor
from ..utils.config import Config


class QueryResponse(BaseModel):
    answer: str
    query_time: datetime
    session_id: Optional[str]
    metadata: Optional[dict] = None


class ResponseGenerator:
    """Orchestrates the entire query processing pipeline."""

    def __init__(self, config: Config):
        self.config = config
        self.rp_client = ReportPortalClient(config)
        self.cache_manager = CacheManager(config)
        self.query_processor = QueryProcessor()
        self.prompt_engineer = PromptEngineer(config)
        self.llm_interface = LLMInterface(config)
        self.data_normalizer = DataNormalizer()

    async def generate_response(
        self, query: str, session_id: Optional[str] = None
    ) -> QueryResponse:
        """Generate response for a user query."""
        start_time = datetime.now()

        try:
            # Process the query
            query_intent = self.query_processor.process_query(query)
            logger.info(f"Processed query: {query_intent.query_type.value}")

            # Check cache first
            cache_key = f"query_{hash(query)}_{query_intent.filters.dict()}"
            cached_data = self.cache_manager.get(cache_key)

            if cached_data:
                logger.info("Using cached data")
                test_data = cached_data
            else:
                # Fetch data from Report Portal
                test_data = await self._fetch_relevant_data(query_intent)

                # Cache the results
                self.cache_manager.set(cache_key, test_data, ttl_hours=1)

            # Normalize data
            df = self.data_normalizer.normalize_test_executions(test_data)
            summary_stats = self.data_normalizer.create_test_summary(df)
            context = self.data_normalizer.format_for_llm(df)

            # Construct prompt
            prompt = self.prompt_engineer.construct_prompt(query_intent, context, summary_stats)

            # Generate LLM response
            answer = await self.llm_interface.generate_response(prompt)

            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()

            return QueryResponse(
                answer=answer,
                query_time=start_time,
                session_id=session_id,
                metadata={
                    "query_type": query_intent.query_type.value,
                    "response_time_seconds": response_time,
                    "data_points": len(test_data),
                    "statistics": summary_stats,
                },
            )

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return QueryResponse(
                answer=f"I encountered an error while processing your query: {str(e)}",
                query_time=start_time,
                session_id=session_id,
                metadata={"error": str(e)},
            )

    async def generate_streaming_response(
        self, query: str, session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response for real-time output."""
        try:
            # Process query and fetch data (same as above)
            query_intent = self.query_processor.process_query(query)
            test_data = await self._fetch_relevant_data(query_intent)

            # Prepare context
            df = self.data_normalizer.normalize_test_executions(test_data)
            summary_stats = self.data_normalizer.create_test_summary(df)
            context = self.data_normalizer.format_for_llm(df)

            # Construct prompt
            prompt = self.prompt_engineer.construct_prompt(query_intent, context, summary_stats)

            # Stream LLM response
            async for chunk in self.llm_interface.generate_streaming_response(prompt):
                yield chunk

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield f"\nError: {str(e)}"

    async def _fetch_relevant_data(self, query_intent):
        """Fetch relevant test data based on query intent."""
        filters = query_intent.filters

        # Build Report Portal filter parameters
        rp_filters = {}

        if filters.time_filter:
            # Convert days_back to timestamp
            from_date = datetime.now() - timedelta(days=filters.time_filter.days_back)
            rp_filters["filter.gte.startTime"] = int(from_date.timestamp() * 1000)

        if filters.status and filters.status != "all":
            rp_filters["filter.eq.status"] = filters.status.upper()

        if filters.platform:
            rp_filters["filter.has.attributes"] = f"platform:{filters.platform}"

        # Fetch launches first
        launches = await self.rp_client.get_launches(rp_filters, page_size=50)

        # Fetch test items
        all_test_items = []
        for launch in launches[:10]:  # Limit to recent launches
            items = await self.rp_client.get_test_items(launch.id)
            all_test_items.extend(items)

        # Filter by specific test names if provided
        if query_intent.test_names:
            all_test_items = [
                item
                for item in all_test_items
                if any(name in item.name for name in query_intent.test_names)
            ]

        return all_test_items

    async def close(self):
        """Cleanup resources."""
        await self.rp_client.close()
