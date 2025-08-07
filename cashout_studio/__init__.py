"""
CashoutStudio-v1: Offline AI tuning canvas + Web3 signatures with ECU support
"""

__version__ = "1.0.0"
__author__ = "eedgurr"

from .ecu import ECUManager
from .bridge import ECUBridge

__all__ = ["ECUManager", "ECUBridge"]