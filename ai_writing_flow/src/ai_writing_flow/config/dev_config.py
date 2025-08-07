"""
Development Configuration and Optimization - Task 11.2

Configuration for local development optimizations including:
- Hot reload support
- Caching configurations
- Development shortcuts
- Performance optimizations
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class DevelopmentConfig:
    """Development-specific configuration"""
    
    # Development mode flags
    dev_mode: bool = field(default_factory=lambda: os.getenv("DEV_MODE", "true").lower() == "true")
    hot_reload: bool = field(default_factory=lambda: os.getenv("HOT_RELOAD", "true").lower() == "true")
    skip_validation: bool = field(default_factory=lambda: os.getenv("SKIP_VALIDATION", "false").lower() == "true")
    
    # Caching configurations
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    cache_dir: str = ".cache/dev"
    
    # Performance optimizations
    use_smaller_models: bool = True
    model_override: Optional[str] = "gpt-3.5-turbo"  # Faster for dev
    max_concurrent_agents: int = 2  # Limit for local resources
    request_timeout: int = 30  # Shorter timeout for dev
    
    # Knowledge Base optimizations
    kb_cache_enabled: bool = True
    kb_cache_size: int = 100  # Number of cached queries
    kb_local_fallback: bool = True  # Use local files if KB unavailable
    
    # Development shortcuts
    auto_approve_human_review: bool = field(default_factory=lambda: os.getenv("AUTO_APPROVE", "false").lower() == "true")
    mock_external_services: bool = field(default_factory=lambda: os.getenv("MOCK_SERVICES", "false").lower() == "true")
    verbose_logging: bool = field(default_factory=lambda: os.getenv("VERBOSE", "true").lower() == "true")
    
    # UI optimizations
    ui_update_interval_ms: int = 1000  # Less frequent updates for performance
    disable_animations: bool = True
    
    # File watching for hot reload
    watch_paths: List[str] = field(default_factory=lambda: [
        "src/ai_writing_flow",
        "config",
        "prompts"
    ])
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "*.pyc",
        "__pycache__",
        "*.log",
        ".cache"
    ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "dev_mode": self.dev_mode,
            "hot_reload": self.hot_reload,
            "skip_validation": self.skip_validation,
            "caching": {
                "enabled": self.enable_cache,
                "ttl": self.cache_ttl_seconds,
                "dir": self.cache_dir
            },
            "performance": {
                "smaller_models": self.use_smaller_models,
                "model": self.model_override,
                "max_concurrent": self.max_concurrent_agents,
                "timeout": self.request_timeout
            },
            "kb": {
                "cache_enabled": self.kb_cache_enabled,
                "cache_size": self.kb_cache_size,
                "local_fallback": self.kb_local_fallback
            },
            "shortcuts": {
                "auto_approve": self.auto_approve_human_review,
                "mock_services": self.mock_external_services,
                "verbose": self.verbose_logging
            }
        }
    
    def save(self, path: Optional[str] = None):
        """Save configuration to file"""
        if not path:
            path = "config/dev_config.json"
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> 'DevelopmentConfig':
        """Load configuration from file"""
        if not path:
            path = "config/dev_config.json"
        
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                # Map saved structure to class attributes
                config_dict = {}
                
                # Direct mappings
                direct_keys = ['dev_mode', 'hot_reload', 'skip_validation']
                for key in direct_keys:
                    if key in data:
                        config_dict[key] = data[key]
                
                # Caching section
                if 'caching' in data:
                    config_dict['enable_cache'] = data['caching'].get('enabled', True)
                    config_dict['cache_ttl_seconds'] = data['caching'].get('ttl', 3600)
                    config_dict['cache_dir'] = data['caching'].get('dir', '.cache/dev')
                
                # Performance section
                if 'performance' in data:
                    config_dict['use_smaller_models'] = data['performance'].get('smaller_models', True)
                    config_dict['model_override'] = data['performance'].get('model', 'gpt-3.5-turbo')
                    config_dict['max_concurrent_agents'] = data['performance'].get('max_concurrent', 2)
                    config_dict['request_timeout'] = data['performance'].get('timeout', 30)
                
                # KB section
                if 'kb' in data:
                    config_dict['kb_cache_enabled'] = data['kb'].get('cache_enabled', True)
                    config_dict['kb_cache_size'] = data['kb'].get('cache_size', 100)
                    config_dict['kb_local_fallback'] = data['kb'].get('local_fallback', True)
                
                # Shortcuts section
                if 'shortcuts' in data:
                    config_dict['auto_approve_human_review'] = data['shortcuts'].get('auto_approve', False)
                    config_dict['mock_external_services'] = data['shortcuts'].get('mock_services', False)
                    config_dict['verbose_logging'] = data['shortcuts'].get('verbose', True)
                
                return cls(**config_dict)
        
        return cls()  # Return default config


# Global development config instance
_dev_config: Optional[DevelopmentConfig] = None

def get_dev_config() -> DevelopmentConfig:
    """Get or create development configuration"""
    global _dev_config
    if _dev_config is None:
        _dev_config = DevelopmentConfig.load()
    return _dev_config

def reload_dev_config():
    """Reload development configuration (for hot reload)"""
    global _dev_config
    _dev_config = DevelopmentConfig.load()
    return _dev_config