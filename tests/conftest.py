import pytest
import asyncio
from pathlib import Path
import shutil


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files"""
    yield tmp_path
    # Cleanup
    if tmp_path.exists():
        shutil.rmtree(tmp_path)


@pytest.fixture
def test_config(temp_dir):
    """Create test configuration"""
    from src.utils.config import Config
    
    config = Config(
        reportportal={
            "base_url": "http://test.reportportal.com",
            "project": "test_project",
            "auth_token": "test_token"
        },
        llm={
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "api_key": "test_key",
            "temperature": 0.7,
            "max_tokens": 2000
        },
        cache={
            "enabled": True,
            "directory": str(temp_dir / "cache"),
            "ttl_hours": 1
        },
        paths={
            "session_dir": str(temp_dir / "sessions"),
            "prompts_file": str(temp_dir / "prompts.yaml"),
            "logs_dir": str(temp_dir / "logs")
        }
    )
    
    # Create directories
    for path in [config.cache.directory, config.paths.session_dir, config.paths.logs_dir]:
        Path(path).mkdir(parents=True, exist_ok=True)
    
    return config