import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.application.response_generator import ResponseGenerator, QueryResponse
from src.models.query_models import QueryIntent, FilterCriteria, QueryType
from src.models.test_execution import TestExecution
from src.utils.config import Config


@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.reportportal.base_url = "http://test.reportportal.com"
    config.reportportal.project = "test_project"
    config.reportportal.auth_token = "test_token"
    config.llm.provider = "openai"
    config.llm.model_name = "gpt-3.5-turbo"
    config.cache.enabled = True
    config.cache.directory = "./test_cache"
    config.cache.ttl_hours = 1
    return config


@pytest.fixture
def response_generator(mock_config):
    with patch('src.application.response_generator.ReportPortalClient'):
        with patch('src.application.response_generator.CacheManager'):
            with patch('src.application.response_generator.LLMInterface'):
                return ResponseGenerator(mock_config)


class TestResponseGenerator:
    @pytest.mark.asyncio
    async def test_generate_response_success(self, response_generator):
        # Mock query intent
        mock_intent = QueryIntent(
            original_query="Show failed tests on AWS",
            query_type=QueryType.STATUS_CHECK,
            filters=FilterCriteria(status="failed", platform="aws"),
            test_names=[],
            requires_aggregation=False
        )
        
        # Mock test data
        mock_test_data = [
            TestExecution(
                id="test1",
                name="test_example",
                type="TEST",
                startTime=1640000000000,
                endTime=1640000060000,
                status="FAILED",
                launchId="launch1",
                attributes={"platform": "aws"},
                tags=["smoke"]
            )
        ]
        
        # Configure mocks
        response_generator.query_processor.process_query = MagicMock(return_value=mock_intent)
        response_generator.cache_manager.get = MagicMock(return_value=None)
        response_generator._fetch_relevant_data = AsyncMock(return_value=mock_test_data)
        response_generator.llm_interface.generate_response = AsyncMock(
            return_value="I found 1 failed test on AWS: test_example"
        )
        
        # Execute
        response = await response_generator.generate_response("Show failed tests on AWS")
        
        # Assertions
        assert isinstance(response, QueryResponse)
        assert "failed test on AWS" in response.answer
        assert response.metadata["query_type"] == "status_check"
        assert response.metadata["data_points"] == 1
    
    @pytest.mark.asyncio
    async def test_generate_response_with_cache(self, response_generator):
        # Mock cached data
        cached_data = [
            TestExecution(
                id="test1",
                name="test_cached",
                type="TEST",
                startTime=1640000000000,
                endTime=1640000060000,
                status="PASSED",
                launchId="launch1",
                attributes={},
                tags=[]
            )
        ]
        
        # Configure mocks
        response_generator.cache_manager.get = MagicMock(return_value=cached_data)
        response_generator.llm_interface.generate_response = AsyncMock(
            return_value="Found cached test result"
        )
        
        # Execute
        response = await response_generator.generate_response("Show test_cached status")
        
        # Assertions
        assert "cached test result" in response.answer
        # Verify we didn't fetch from Report Portal
        response_generator._fetch_relevant_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, response_generator):
        # Mock streaming chunks
        async def mock_stream(*args, **kwargs):
            chunks = ["Finding ", "failed ", "tests..."]
            for chunk in chunks:
                yield chunk
        
        # Configure mocks
        response_generator._fetch_relevant_data = AsyncMock(return_value=[])
        response_generator.llm_interface.generate_response = mock_stream
        
        # Execute
        chunks = []
        async for chunk in response_generator.generate_streaming_response("Show failed tests"):
            chunks.append(chunk)
        
        # Assertions
        assert len(chunks) == 3
        assert "".join(chunks) == "Finding failed tests..."