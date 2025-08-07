"""
Core ECU management and communication framework
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging
from loguru import logger

class ECUType(Enum):
    """Supported ECU types"""
    BOSCH_ME17 = "bosch_me17"
    SIEMENS_MSV = "siemens_msv" 
    DENSO_SH705X = "denso_sh705x"

class ConnectionType(Enum):
    """Connection methods for ECUs"""
    SERIAL = "serial"
    CAN_BUS = "can_bus"
    USB = "usb"
    ETHERNET = "ethernet"

@dataclass
class ECUConfig:
    """Configuration for ECU connection"""
    ecu_type: ECUType
    connection_type: ConnectionType
    port: str
    baud_rate: int = 38400
    can_bitrate: int = 500000
    timeout: float = 5.0
    retries: int = 3

class ECUProtocol(ABC):
    """Abstract base class for ECU communication protocols"""
    
    def __init__(self, config: ECUConfig):
        self.config = config
        self.connected = False
        self._connection = None
        
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to ECU"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from ECU"""
        pass
    
    @abstractmethod
    def read_data(self, address: int, length: int) -> bytes:
        """Read data from ECU memory"""
        pass
    
    @abstractmethod
    def write_data(self, address: int, data: bytes) -> bool:
        """Write data to ECU memory"""
        pass
    
    @abstractmethod
    def get_ecu_info(self) -> Dict[str, Any]:
        """Get ECU identification and version info"""
        pass
    
    @abstractmethod
    def get_dtc_codes(self) -> List[str]:
        """Get diagnostic trouble codes"""
        pass
    
    @abstractmethod
    def clear_dtc_codes(self) -> bool:
        """Clear diagnostic trouble codes"""
        pass

class ECUManager:
    """Central manager for all ECU communications"""
    
    def __init__(self):
        self._protocols: Dict[ECUType, ECUProtocol] = {}
        self._active_ecu: Optional[ECUType] = None
        logger.info("ECUManager initialized")
    
    def register_protocol(self, ecu_type: ECUType, protocol: ECUProtocol):
        """Register a protocol handler for an ECU type"""
        self._protocols[ecu_type] = protocol
        logger.info(f"Registered protocol for {ecu_type.value}")
    
    def connect_ecu(self, ecu_type: ECUType) -> bool:
        """Connect to a specific ECU"""
        if ecu_type not in self._protocols:
            logger.error(f"No protocol registered for {ecu_type.value}")
            return False
        
        try:
            protocol = self._protocols[ecu_type]
            if protocol.connect():
                self._active_ecu = ecu_type
                logger.success(f"Connected to {ecu_type.value}")
                return True
            else:
                logger.error(f"Failed to connect to {ecu_type.value}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to {ecu_type.value}: {str(e)}")
            return False
    
    def disconnect_ecu(self, ecu_type: Optional[ECUType] = None) -> bool:
        """Disconnect from ECU"""
        target_ecu = ecu_type or self._active_ecu
        if not target_ecu:
            logger.warning("No ECU to disconnect from")
            return True
        
        if target_ecu in self._protocols:
            try:
                success = self._protocols[target_ecu].disconnect()
                if success and target_ecu == self._active_ecu:
                    self._active_ecu = None
                logger.info(f"Disconnected from {target_ecu.value}")
                return success
            except Exception as e:
                logger.error(f"Error disconnecting from {target_ecu.value}: {str(e)}")
                return False
        return True
    
    def get_active_protocol(self) -> Optional[ECUProtocol]:
        """Get the currently active ECU protocol"""
        if self._active_ecu:
            return self._protocols.get(self._active_ecu)
        return None
    
    def list_supported_ecus(self) -> List[ECUType]:
        """List all supported ECU types"""
        return list(self._protocols.keys())
    
    def is_connected(self, ecu_type: Optional[ECUType] = None) -> bool:
        """Check if ECU is connected"""
        target_ecu = ecu_type or self._active_ecu
        if target_ecu and target_ecu in self._protocols:
            return self._protocols[target_ecu].connected
        return False