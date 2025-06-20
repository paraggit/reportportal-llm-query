from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class TestIssue(BaseModel):
    issueType: Optional[str] = None
    comment: Optional[str] = None
    autoAnalyzed: bool = False
    ignoreAnalysis: bool = False


class TestExecution(BaseModel):
    id: Union[str, int]
    name: str
    type: str
    startTime: Union[int, float]
    endTime: Optional[Union[int, float]] = None
    status: str
    launchId: Union[str, int]
    parentId: Optional[Union[str, int]] = None
    hasChildren: bool = False
    path: Optional[List[str]] = None
    attributes: Union[Dict[str, Any], List[Dict[str, str]]] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    issue: Optional[TestIssue] = None
    description: Optional[str] = None

    @field_validator("id", "launchId", "parentId", mode="before")
    @classmethod
    def convert_to_string(cls, v):
        if v is not None:
            return str(v)
        return v

    @field_validator("attributes", mode="before")
    @classmethod
    def convert_attributes(cls, v):
        if isinstance(v, list):
            result = {}
            for item in v:
                if isinstance(item, dict) and "key" in item and "value" in item:
                    result[item["key"]] = item["value"]
            return result
        return v or {}

    @field_validator("startTime", "endTime", mode="before")
    @classmethod
    def convert_timestamp(cls, v):
        if v is not None:
            return int(v)
        return v

    @property
    def duration(self) -> Optional[float]:
        if self.endTime and self.startTime:
            return (self.endTime - self.startTime) / 1000.0
        return None

    @property
    def start_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.startTime / 1000)


class Launch(BaseModel):
    id: Union[str, int]
    uuid: str
    name: str
    number: int
    startTime: Union[int, float]
    endTime: Optional[Union[int, float]] = None
    status: str
    attributes: Union[Dict[str, Any], List[Dict[str, str]]] = Field(default_factory=dict)
    mode: str = "DEFAULT"
    analysing: List[str] = Field(default_factory=list)
    approximateDuration: Optional[float] = None
    hasRetries: bool = False
    statistics: Optional[Dict[str, Any]] = None

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_to_string(cls, v):
        if v is not None:
            return str(v)
        return v

    @field_validator("attributes", mode="before")
    @classmethod
    def convert_attributes(cls, v):
        if isinstance(v, list):
            result = {}
            for item in v:
                if isinstance(item, dict) and "key" in item and "value" in item:
                    result[item["key"]] = item["value"]
            return result
        return v or {}

    @field_validator("startTime", "endTime", mode="before")
    @classmethod
    def convert_timestamp(cls, v):
        if v is not None:
            return int(v)
        return v
