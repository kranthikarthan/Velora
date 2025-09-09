"""
Velora: AI Interoperability Layer

A next-generation interoperability layer for seamless AI agent communication,
collaboration, and data exchange across different platforms and domains.
"""

__version__ = "1.0.0"
__author__ = "Velora Team"
__email__ = "team@velora.ai"
__license__ = "Apache-2.0"

from velora.core import VeloraCore
from velora.protocols import UAICP, ANP
from velora.agents import Agent, AgentManager

__all__ = [
    "VeloraCore",
    "UAICP",
    "ANP",
    "Agent",
    "AgentManager",
]