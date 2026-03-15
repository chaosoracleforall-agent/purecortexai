"""
PURECORTEX AI Agent Framework — Phase 4.

Provides the base agent abstraction, persistent memory with feedback loops,
and concrete agent implementations (Senator, Curator, Social) that all use
tri-brain consensus via the ConsensusOrchestrator.
"""

from .base_agent import BaseAgent
from .memory import AgentMemory
from .senator_agent import SenatorAgent
from .curator_agent import CuratorAgent
from .social_agent import SocialAgent
from .orchestrator_loop import AgentOrchestrationLoop

__all__ = [
    "BaseAgent",
    "AgentMemory",
    "SenatorAgent",
    "CuratorAgent",
    "SocialAgent",
    "AgentOrchestrationLoop",
]
