import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class ReportPortalConfig(BaseModel):
    base_url: str = Field(default="https://localhost:8080")
    project: str = Field(default="default_personal")
    auth_token: str = Field(default="")
    verify_ssl: bool = Field(default=False)


class LLMConfig(BaseModel):
    provider: str = Field(default="openai")
    model_name: str = Field(default="gpt-3.5-turbo")
    api_key: Optional[str] = Field(default=None)
    model_path: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    context_length: int = Field(default=4096)
    gpu_layers: int = Field(default=0)


class CacheConfig(BaseModel):
    enabled: bool = Field(default=True)
    directory: str = Field(default="./cache")
    ttl_hours: int = Field(default=24)


class PathConfig(BaseModel):
    session_dir: str = Field(default="./sessions")
    prompts_file: str = Field(default="config/prompts.yaml")
    logs_dir: str = Field(default="./logs")


class Config(BaseModel):
    reportportal: ReportPortalConfig = Field(default_factory=ReportPortalConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    paths: PathConfig = Field(default_factory=PathConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            # Return default config if file doesn't exist
            return cls()

        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)

        # Override with environment variables if present
        config_data = cls._override_with_env(config_data)

        return cls(**config_data)

    @staticmethod
    def _override_with_env(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Override config values with environment variables."""
        env_mappings = {
            "REPORTPORTAL_URL": ("reportportal", "base_url"),
            "REPORTPORTAL_PROJECT": ("reportportal", "project"),
            "REPORTPORTAL_TOKEN": ("reportportal", "auth_token"),
            "LLM_PROVIDER": ("llm", "provider"),
            "LLM_MODEL": ("llm", "model_name"),
            "LLM_API_KEY": ("llm", "api_key"),
            "OPENAI_API_KEY": ("llm", "api_key"),
        }

        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                if section not in config_data:
                    config_data[section] = {}
                config_data[section][key] = value

        return config_data
