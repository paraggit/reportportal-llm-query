import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import httpx
from loguru import logger
from pydantic import BaseModel, Field
import ssl
import certifi

from ..models.test_execution import TestExecution, Launch
from ..utils.config import Config


class ReportPortalClient:
    """Client for interacting with Report Portal API"""
    
    def __init__(self, config: Config):
        self.base_url = config.reportportal.base_url
        self.project = config.reportportal.project
        self.auth_token = config.reportportal.auth_token
        
        # Handle SSL verification
        verify = True
        if hasattr(config.reportportal, 'verify_ssl'):
            verify = config.reportportal.verify_ssl
        
        # Create SSL context
        if not verify:
            # Disable SSL verification for self-signed certificates
            logger.warning("SSL verification is disabled. This is not recommended for production!")
            ssl_context = httpx.create_ssl_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            verify = ssl_context
        else:
            # Use certifi for proper SSL verification
            verify = certifi.where()
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0,
            verify=verify
        )
    
    async def get_launches(
        self, 
        filter_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100
    ) -> List[Launch]:
        """Fetch launches with optional filtering"""
        endpoint = f"/api/v1/{self.project}/launch"
        
        params = {
            "page.size": page_size,
            "page.page": 1,
            "page.sort": "startTime,DESC"
        }
        
        if filter_params:
            params.update(filter_params)
        
        launches = []
        
        try:
            while True:
                response = await self.client.get(endpoint, params=params)
                response.raise_for_status()
                
                data = response.json()
                content = data.get("content", [])
                
                for launch_data in content:
                    launches.append(Launch(**launch_data))
                
                # Check if there are more pages
                if data["page"]["number"] >= data["page"]["totalPages"]:
                    break
                    
                params["page.page"] += 1
                
        except httpx.HTTPError as e:
            logger.error(f"Error fetching launches: {e}")
            raise
        
        return launches
    
    async def get_test_items(
        self, 
        launch_id: str,
        filter_params: Optional[Dict[str, Any]] = None
    ) -> List[TestExecution]:
        """Fetch test items for a specific launch"""
        endpoint = f"/api/v1/{self.project}/item"
        
        params = {
            "filter.eq.launchId": launch_id,
            "page.size": 200,
            "page.page": 1
        }
        
        if filter_params:
            params.update(filter_params)
        
        test_items = []
        
        try:
            while True:
                response = await self.client.get(endpoint, params=params)
                response.raise_for_status()
                
                data = response.json()
                content = data.get("content", [])
                
                for item_data in content:
                    test_items.append(TestExecution(**item_data))
                
                if data["page"]["number"] >= data["page"]["totalPages"]:
                    break
                    
                params["page.page"] += 1
                
        except httpx.HTTPError as e:
            logger.error(f"Error fetching test items: {e}")
            raise
        
        return test_items
    
    async def get_test_history(
        self, 
        test_name: str,
        days_back: int = 30
    ) -> List[TestExecution]:
        """Get historical executions of a specific test"""
        filter_date = datetime.now() - timedelta(days=days_back)
        
        filter_params = {
            "filter.eq.name": test_name,
            "filter.gte.startTime": filter_date.timestamp() * 1000
        }
        
        # First get relevant launches
        launches = await self.get_launches(filter_params)
        
        all_test_items = []
        for launch in launches:
            items = await self.get_test_items(
                launch.id,
                {"filter.eq.name": test_name}
            )
            all_test_items.extend(items)
        
        return all_test_items
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()