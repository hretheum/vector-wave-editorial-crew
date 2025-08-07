"""
AI Writing Flow API Package

This package provides REST API endpoints for integrating with the AI Writing Flow V2 system.
Includes endpoints for flow execution, monitoring, and system management.
"""

from .endpoints import FlowAPI, create_flow_app

__all__ = ["FlowAPI", "create_flow_app"]