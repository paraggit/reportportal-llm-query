import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.data_access.reportportal_client import ReportPortalClient
from src.models.test_execution import TestExecution, Launch
from src.utils.config import Config


@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.reportportal.base_url = "http://test.reportportal.com"
    config.reportportal.project = "test_project"
    config.reportportal.auth_token = "test_token"
    return config


@pytest.fixture
def rp_client(mock_config):
    return ReportPortalClient(mock_config)


class TestReportPortalClient:
    @pytest.mark.asyncio
    async def test_get_launches_success(self, rp_client):
        # Mock response
        mock_response = {
            "content": [
                {
                    "id": "launch1",
                    "uuid": "uuid1",
                    "name": "Test Launch",
                    "number": 1,
                    "startTime": 1640000000000,
                    "status": "PASSED",
                    "attributes": {},
                    "mode": "DEFAULT",
                    "analysing": [],
                    "hasRetries": False
                }
            ],
            "page": {
                "number": 1,
                "totalPages": 1
            }
        }
        
        # Mock the HTTP client
        with patch.object(rp_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = MagicMock()
            
            launches = await rp_client.get_launches()
            
            assert len(launches) == 1
            assert isinstance(launches[0], Launch)
            assert launches[0].id == "launch1"
            assert launches[0].name == "Test Launch"
    
    @pytest.mark.asyncio
    async def test_get_test_items_success(self, rp_client):
        # Mock response
        mock_response = {
            "content": [
                {
                    "id": "item1",
                    "name": "test_example",
                    "type": "TEST",
                    "startTime": 1640000000000,
                    "endTime": 1640000060000,
                    "status": "FAILED",
                    "launchId": "launch1",
                    "hasChildren": False,
                    "attributes": {"platform": "aws"},
                    "tags": ["smoke"],
                    "issue": {
                        "issueType": "PRODUCT_BUG",
                        "comment": "Test failed due to timeout"
                    }
                }
            ],
            "page": {
                "number": 1,
                "totalPages": 1
            }
        }
        
        with patch.object(rp_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = MagicMock()
            
            items = await rp_client.get_test_items("launch1")
            
            assert len(items) == 1
            assert isinstance(items[0], TestExecution)
            assert items[0].id == "item1"
            assert items[0].status == "FAILED"
            assert items[0].attributes["platform"] == "aws"
    
    @pytest.mark.asyncio
    async def test_get_test_history(self, rp_client):
        # Mock launches response
        mock_launches = {
            "content": [
                {
                    "id": "launch1",
                    "uuid": "uuid1",
                    "name": "Test Launch",
                    "number": 1,
                    "startTime": 1640000000000,
                    "status": "PASSED",
                    "attributes": {},
                    "mode": "DEFAULT",
                    "analysing": [],
                    "hasRetries": False
                }
            ],
            "page": {"number": 1, "totalPages": 1}
        }
        
        # Mock test items response
        mock_items = {
            "content": [
                {
                    "id": "item1",
                    "name": "test_specific",
                    "type": "TEST",
                    "startTime": 1640000000000,
                    "endTime": 1640000060000,
                    "status": "PASSED",
                    "launchId": "launch1",
                    "hasChildren": False,
                    "attributes": {},
                    "tags": []
                }
            ],
            "page": {"number": 1, "totalPages": 1}
        }
        
        with patch.object(rp_client.client, 'get', new_callable=AsyncMock) as mock_get:
            # Configure mock to return different responses
            mock_get.side_effect = [
                MagicMock(json=MagicMock(return_value=mock_launches)),
                MagicMock(json=MagicMock(return_value=mock_items))
            ]
            
            history = await rp_client.get_test_history("test_specific", days_back=7)
            
            assert len(history) == 1
            assert history[0].name == "test_specific"
            assert history[0].status == "PASSED"