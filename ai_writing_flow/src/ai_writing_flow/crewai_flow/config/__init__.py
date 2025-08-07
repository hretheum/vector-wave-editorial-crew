"""
CrewAI Configuration Module

Contains configuration management for CrewAI components:
- AgentsConfig: Configuration for all agents
- TasksConfig: Configuration for all tasks

Provides centralized configuration management for the CrewAI flow.
"""

from .agents_config import AgentsConfig
from .tasks_config import TasksConfig

__all__ = [
    "AgentsConfig",
    "TasksConfig",
]