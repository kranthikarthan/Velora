"""
Velora Legacy System Integration

Support for mainframe, COBOL, CICS, and legacy banking systems.
"""

from velora.legacy.bridge import LegacyBridge
from velora.legacy.iso20022 import ISO20022Handler
from velora.legacy.cobol import COBOLCopybookParser
from velora.legacy.cics import CICSGateway

__all__ = [
    "LegacyBridge",
    "ISO20022Handler",
    "COBOLCopybookParser",
    "CICSGateway",
]