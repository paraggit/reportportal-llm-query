from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TestIssue(BaseModel):
    issueType: Optional[str] = None
    comment: Optional[str] = None
    autoAnalyzed: bool = False
    ignoreAnalysis: bool = False


class TestExecution(BaseModel):
    id: str
    name: str
    type: str
    startTime: int
    endTime: Optional[int] = None
    status: str
    launchId: str
    parentId: Optional[str] = None
    hasChildren: bool = False
    path: Optional[List[str]] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    issue: Optional[TestIssue] = None
    description: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate test duration in seconds"""
        if self.endTime:
            return (self.endTime - self.startTime) / 1000.0
        return None
    
    @property
    def start_datetime(self) -> datetime:
        """Convert start time to datetime"""
        return datetime.fromtimestamp(self.startTime / 1000)


class Launch(BaseModel):
    id: str
    uuid: str
    name: str
    number: int
    startTime: int
    endTime: Optional[int] = None
    status: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    mode: str = "DEFAULT"
    analysing: List[str] = Field(default_factory=list)
    approximateDuration: Optional[float] = None
    hasRetries: bool = False
    statistics: Optional[Dict[str, Any]] = None