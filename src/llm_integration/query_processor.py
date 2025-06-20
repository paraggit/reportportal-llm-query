import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from loguru import logger
from pydantic import BaseModel

from ..models.query_models import QueryIntent, TimeFilter, FilterCriteria, QueryType


class QueryProcessor:
    """Process natural language queries to extract intent and parameters"""
    
    def __init__(self):
        self.time_patterns = {
            r'last (\d+) days?': self._parse_days,
            r'past (\d+) weeks?': self._parse_weeks,
            r'last (\d+) hours?': self._parse_hours,
            r'since (\d{4}-\d{2}-\d{2})': self._parse_date,
            r'today': lambda _: 1,
            r'yesterday': lambda _: 1,
            r'this week': lambda _: 7,
            r'last week': lambda _: 14
        }
        
        self.status_keywords = {
            'failed': ['failed', 'failure', 'failing', 'broken'],
            'passed': ['passed', 'passing', 'successful', 'green'],
            'skipped': ['skipped', 'skip', 'ignored'],
            'all': ['all', 'any', 'every']
        }
    
    def process_query(self, query: str) -> QueryIntent:
        """Extract intent and parameters from natural language query"""
        query_lower = query.lower()
        
        # Determine query type
        query_type = self._identify_query_type(query_lower)
        
        # Extract filters
        filters = self._extract_filters(query_lower)
        
        # Extract specific entities
        test_names = self._extract_test_names(query)
        
        return QueryIntent(
            original_query=query,
            query_type=query_type,
            filters=filters,
            test_names=test_names,
            requires_aggregation=self._requires_aggregation(query_lower)
        )
    
    def _identify_query_type(self, query: str) -> QueryType:
        """Identify the type of query"""
        if any(word in query for word in ['flaky', 'unstable', 'intermittent']):
            return QueryType.FLAKY_ANALYSIS
        elif any(word in query for word in ['owner', 'owned by', 'who owns']):
            return QueryType.OWNER_QUERY
        elif any(word in query for word in ['statistics', 'summary', 'report']):
            return QueryType.STATISTICS
        elif any(word in query for word in ['history', 'trend', 'over time']):
            return QueryType.HISTORY_QUERY
        elif any(word in query for word in ['platform', 'aws', 'gcp', 'azure']):
            return QueryType.PLATFORM_SPECIFIC
        elif any(word in query for word in ['status', 'failed', 'passed']):
            return QueryType.STATUS_CHECK
        else:
            return QueryType.GENERAL
    
    def _extract_filters(self, query: str) -> FilterCriteria:
        """Extract filter criteria from query"""
        filters = FilterCriteria()
        
        # Extract time filter
        for pattern, parser in self.time_patterns.items():
            match = re.search(pattern, query)
            if match:
                days_back = parser(match)
                filters.time_filter = TimeFilter(days_back=days_back)
                break
        
        # Extract status filter
        for status, keywords in self.status_keywords.items():
            if any(keyword in query for keyword in keywords):
                filters.status = status
                break
        
        # Extract platform
        platforms = ['aws', 'gcp', 'azure', 'vsphere', 'openstack']
        for platform in platforms:
            if platform in query:
                filters.platform = platform
                break
        
        # Extract owner
        owner_match = re.search(r'owned by (\w+)', query)
        if owner_match:
            filters.owner = owner_match.group(1)
        
        return filters
    
    def _extract_test_names(self, query: str) -> List[str]:
        """Extract specific test names from query"""
        # Look for quoted test names
        quoted_tests = re.findall(r'"([^"]+)"', query)
        
        # Look for test patterns (e.g., test_something)
        test_patterns = re.findall(r'test_\w+', query)
        
        return list(set(quoted_tests + test_patterns))
    
    def _requires_aggregation(self, query: str) -> bool:
        """Determine if query requires aggregation"""
        aggregation_keywords = [
            'how many', 'count', 'total', 'average', 'mean',
            'distribution', 'percentage', 'rate', 'top', 'most'
        ]
        return any(keyword in query for keyword in aggregation_keywords)
    
    @staticmethod
    def _parse_days(match) -> int:
        return int(match.group(1))
    
    @staticmethod
    def _parse_weeks(match) -> int:
        return int(match.group(1)) * 7
    
    @staticmethod
    def _parse_hours(match) -> int:
        return 1  # Convert to days
    
    @staticmethod
    def _parse_date(match) -> int:
        date_str = match.group(1)
        date = datetime.strptime(date_str, '%Y-%m-%d')
        delta = datetime.now() - date
        return delta.days