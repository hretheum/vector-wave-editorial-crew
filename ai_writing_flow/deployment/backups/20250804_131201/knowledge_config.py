"""
Configuration for Knowledge Base Integration

Environment-based configuration for the Knowledge Adapter
with production-ready defaults and observability settings
"""

import os
from typing import Optional
from pathlib import Path

from src.ai_writing_flow.adapters.knowledge_adapter import SearchStrategy


class KnowledgeConfig:
    """Configuration class for Knowledge Base integration"""
    
    # Knowledge Base API settings
    KB_API_URL: str = os.getenv("KNOWLEDGE_BASE_URL", "http://localhost:8082")
    KB_TIMEOUT: float = float(os.getenv("KNOWLEDGE_TIMEOUT", "10.0"))
    KB_MAX_RETRIES: int = int(os.getenv("KNOWLEDGE_MAX_RETRIES", "3"))
    
    # Search strategy configuration
    DEFAULT_STRATEGY: SearchStrategy = SearchStrategy(
        os.getenv("KNOWLEDGE_STRATEGY", "HYBRID")
    )
    
    # Circuit breaker settings
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))
    
    # File system paths
    DOCS_PATH: Path = Path(os.getenv(
        "CREWAI_DOCS_PATH",
        "/Users/hretheum/dev/bezrobocie/vector-wave/knowledge-base/knowledge-base/data/crewai-docs/docs/en"
    ))
    
    # Performance settings
    DEFAULT_SEARCH_LIMIT: int = int(os.getenv("KNOWLEDGE_SEARCH_LIMIT", "5"))
    DEFAULT_SCORE_THRESHOLD: float = float(os.getenv("KNOWLEDGE_SCORE_THRESHOLD", "0.35"))
    
    # Logging and observability
    LOG_LEVEL: str = os.getenv("KNOWLEDGE_LOG_LEVEL", "INFO")
    ENABLE_METRICS: bool = os.getenv("KNOWLEDGE_ENABLE_METRICS", "true").lower() == "true"
    ENABLE_TRACING: bool = os.getenv("KNOWLEDGE_ENABLE_TRACING", "false").lower() == "true"
    
    # Cache settings
    CACHE_ENABLED: bool = os.getenv("KNOWLEDGE_CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("KNOWLEDGE_CACHE_TTL", "3600"))
    
    # Development settings
    DEBUG_MODE: bool = os.getenv("KNOWLEDGE_DEBUG", "false").lower() == "true"
    BYPASS_KB_FOR_TESTING: bool = os.getenv("BYPASS_KB_FOR_TESTING", "false").lower() == "true"
    
    @classmethod
    def get_adapter_config(cls) -> dict:
        """Get configuration dictionary for KnowledgeAdapter initialization"""
        return {
            "strategy": cls.DEFAULT_STRATEGY,
            "kb_api_url": cls.KB_API_URL,
            "timeout": cls.KB_TIMEOUT,
            "max_retries": cls.KB_MAX_RETRIES,
            "circuit_breaker_threshold": cls.CIRCUIT_BREAKER_THRESHOLD,
            "docs_path": str(cls.DOCS_PATH)
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @classmethod
    def validate_config(cls) -> list:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check if docs path exists
        if not cls.DOCS_PATH.exists():
            issues.append(f"Documentation path not found: {cls.DOCS_PATH}")
        
        # Validate timeout values
        if cls.KB_TIMEOUT <= 0:
            issues.append(f"Invalid timeout: {cls.KB_TIMEOUT}")
        
        # Validate retry count
        if cls.KB_MAX_RETRIES < 0:
            issues.append(f"Invalid max retries: {cls.KB_MAX_RETRIES}")
        
        # Validate score threshold
        if not 0.0 <= cls.DEFAULT_SCORE_THRESHOLD <= 1.0:
            issues.append(f"Invalid score threshold: {cls.DEFAULT_SCORE_THRESHOLD}")
        
        return issues


# Environment configuration templates
DEVELOPMENT_ENV = """
# Development Environment Configuration for Knowledge Base
export KNOWLEDGE_STRATEGY="FILE_FIRST"
export KNOWLEDGE_BASE_URL="http://localhost:8082"
export KNOWLEDGE_TIMEOUT="5.0"
export KNOWLEDGE_MAX_RETRIES="2"
export KNOWLEDGE_DEBUG="true"
export BYPASS_KB_FOR_TESTING="true"
"""

PRODUCTION_ENV = """
# Production Environment Configuration for Knowledge Base
export KNOWLEDGE_STRATEGY="HYBRID"
export KNOWLEDGE_BASE_URL="https://kb.vectorwave.dev"
export KNOWLEDGE_TIMEOUT="10.0"
export KNOWLEDGE_MAX_RETRIES="3"
export CIRCUIT_BREAKER_THRESHOLD="10"
export KNOWLEDGE_ENABLE_METRICS="true"
export KNOWLEDGE_ENABLE_TRACING="true"
export ENVIRONMENT="production"
"""

TESTING_ENV = """
# Testing Environment Configuration for Knowledge Base
export KNOWLEDGE_STRATEGY="FILE_FIRST"
export KNOWLEDGE_TIMEOUT="2.0"
export KNOWLEDGE_MAX_RETRIES="1"
export BYPASS_KB_FOR_TESTING="true"
export KNOWLEDGE_DEBUG="true"
"""


def print_current_config():
    """Print current configuration for debugging"""
    print("🔧 Current Knowledge Base Configuration:")
    print(f"  Strategy: {KnowledgeConfig.DEFAULT_STRATEGY.value}")
    print(f"  KB API URL: {KnowledgeConfig.KB_API_URL}")
    print(f"  Timeout: {KnowledgeConfig.KB_TIMEOUT}s")
    print(f"  Max Retries: {KnowledgeConfig.KB_MAX_RETRIES}")
    print(f"  Docs Path: {KnowledgeConfig.DOCS_PATH}")
    print(f"  Debug Mode: {KnowledgeConfig.DEBUG_MODE}")
    
    issues = KnowledgeConfig.validate_config()
    if issues:
        print("⚠️  Configuration Issues:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("✅ Configuration is valid")


if __name__ == "__main__":
    print_current_config()