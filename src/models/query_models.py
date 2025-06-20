from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class QueryType(Enum):
    STATUS_CHECK = "status_check"
    HISTORY_QUERY = "history_query"
    STATISTICS = "statistics"
    FLAKY_ANALYSIS = "flaky_analysis"
    OWNER_QUERY = "owner_query"
    PLATFORM_SPECIFIC = "platform_specific"
    GENERAL = "general"


class TimeFilter(BaseModel):
    days_back: int = 7
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class FilterCriteria(BaseModel):
    time_filter: Optional[TimeFilter] = None
    status: Optional[str] = None
    platform: Optional[str] = None
    owner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class QueryIntent(BaseModel):
    original_query: str
    query_type: QueryType
    filters: FilterCriteria
    test_names: List[str] = Field(default_factory=list)
    requires_aggregation: bool = False
