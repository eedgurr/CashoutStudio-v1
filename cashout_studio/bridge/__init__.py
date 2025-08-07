"""
ECU Bridge Layer - Provides unified interface for all ECU communications
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import json
import time
from loguru import logger

from ..ecu import ECUManager, ECUType, ECUConfig, ConnectionType
from ..protocols import BoschME17Protocol, SiemensMSVProtocol, DensoSH705xProtocol


@dataclass 
class ECUSession:
    """Represents an active ECU communication session"""
    ecu_type: ECUType
    config: ECUConfig
    info: Dict[str, Any]
    connected_at: float
    
    
class ECUBridge:
    """
    Unified bridge layer for ECU communications
    
    Provides a high-level interface that abstracts the different ECU protocols
    and provides consistent methods for interacting with all supported ECUs.
    """
    
    def __init__(self):
        self.manager = ECUManager()
        self.sessions: Dict[ECUType, ECUSession] = {}
        self._initialize_protocols()
        logger.info("ECU Bridge initialized")
    
    def _initialize_protocols(self):
        """Initialize and register all supported ECU protocols"""
        # Note: These are placeholder configs - real implementation would load from config files
        
        # Register Bosch ME17
        bosch_config = ECUConfig(
            ecu_type=ECUType.BOSCH_ME17,
            connection_type=ConnectionType.SERIAL,
            port="/dev/ttyUSB0",
            baud_rate=38400
        )
        bosch_protocol = BoschME17Protocol(bosch_config)
        self.manager.register_protocol(ECUType.BOSCH_ME17, bosch_protocol)
        
        # Register Siemens MSV  
        siemens_config = ECUConfig(
            ecu_type=ECUType.SIEMENS_MSV,
            connection_type=ConnectionType.CAN_BUS,
            port="can0",
            can_bitrate=500000
        )
        siemens_protocol = SiemensMSVProtocol(siemens_config)
        self.manager.register_protocol(ECUType.SIEMENS_MSV, siemens_protocol)
        
        # Register Denso SH705x
        denso_config = ECUConfig(
            ecu_type=ECUType.DENSO_SH705X,
            connection_type=ConnectionType.SERIAL,
            port="/dev/ttyUSB1", 
            baud_rate=19200
        )
        denso_protocol = DensoSH705xProtocol(denso_config)
        self.manager.register_protocol(ECUType.DENSO_SH705X, denso_protocol)
    
    def configure_ecu(self, ecu_type: ECUType, config: ECUConfig) -> bool:
        """Configure or reconfigure an ECU with new settings"""
        try:
            if ecu_type == ECUType.BOSCH_ME17:
                protocol = BoschME17Protocol(config)
            elif ecu_type == ECUType.SIEMENS_MSV:
                protocol = SiemensMSVProtocol(config)
            elif ecu_type == ECUType.DENSO_SH705X:
                protocol = DensoSH705xProtocol(config)
            else:
                logger.error(f"Unsupported ECU type: {ecu_type}")
                return False
            
            self.manager.register_protocol(ecu_type, protocol)
            logger.info(f"Configured {ecu_type.value} with new settings")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring {ecu_type.value}: {str(e)}")
            return False
    
    def connect(self, ecu_type: ECUType) -> bool:
        """Connect to an ECU and create a session"""
        try:
            if self.manager.connect_ecu(ecu_type):
                protocol = self.manager.get_active_protocol()
                if protocol:
                    # Get ECU info and create session
                    ecu_info = protocol.get_ecu_info()
                    session = ECUSession(
                        ecu_type=ecu_type,
                        config=protocol.config,
                        info=ecu_info,
                        connected_at=time.time()
                    )
                    self.sessions[ecu_type] = session
                    
                    logger.success(f"Created session for {ecu_type.value}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error creating session for {ecu_type.value}: {str(e)}")
            return False
    
    def disconnect(self, ecu_type: Optional[ECUType] = None) -> bool:
        """Disconnect from ECU and clean up session"""
        try:
            success = self.manager.disconnect_ecu(ecu_type)
            
            # Clean up session
            target_ecu = ecu_type or self.manager._active_ecu
            if target_ecu and target_ecu in self.sessions:
                del self.sessions[target_ecu]
                logger.info(f"Cleaned up session for {target_ecu.value}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
            return False
    
    def read_memory(self, address: int, length: int, ecu_type: Optional[ECUType] = None) -> bytes:
        """Read data from ECU memory"""
        protocol = self._get_protocol(ecu_type)
        if not protocol:
            raise Exception("No active ECU connection")
        
        return protocol.read_data(address, length)
    
    def write_memory(self, address: int, data: bytes, ecu_type: Optional[ECUType] = None) -> bool:
        """Write data to ECU memory"""
        protocol = self._get_protocol(ecu_type)
        if not protocol:
            raise Exception("No active ECU connection")
        
        return protocol.write_data(address, data)
    
    def get_ecu_info(self, ecu_type: Optional[ECUType] = None) -> Dict[str, Any]:
        """Get ECU information"""
        protocol = self._get_protocol(ecu_type)
        if not protocol:
            return {}
        
        return protocol.get_ecu_info()
    
    def get_diagnostic_codes(self, ecu_type: Optional[ECUType] = None) -> List[str]:
        """Get diagnostic trouble codes"""
        protocol = self._get_protocol(ecu_type)
        if not protocol:
            return []
        
        return protocol.get_dtc_codes()
    
    def clear_diagnostic_codes(self, ecu_type: Optional[ECUType] = None) -> bool:
        """Clear diagnostic trouble codes"""
        protocol = self._get_protocol(ecu_type)
        if not protocol:
            return False
        
        return protocol.clear_dtc_codes()
    
    def get_active_session(self) -> Optional[ECUSession]:
        """Get information about the active ECU session"""
        active_ecu = self.manager._active_ecu
        if active_ecu and active_ecu in self.sessions:
            return self.sessions[active_ecu]
        return None
    
    def list_sessions(self) -> Dict[ECUType, ECUSession]:
        """List all active ECU sessions"""
        return self.sessions.copy()
    
    def is_connected(self, ecu_type: Optional[ECUType] = None) -> bool:
        """Check if ECU is connected"""
        return self.manager.is_connected(ecu_type)
    
    def get_supported_ecus(self) -> List[ECUType]:
        """Get list of all supported ECU types"""
        return self.manager.list_supported_ecus()
    
    def export_session_data(self, ecu_type: Optional[ECUType] = None) -> Dict[str, Any]:
        """Export session data for analysis or storage"""
        session = self.sessions.get(ecu_type or self.manager._active_ecu)
        if not session:
            return {}
        
        return {
            'ecu_type': session.ecu_type.value,
            'config': {
                'connection_type': session.config.connection_type.value,
                'port': session.config.port,
                'baud_rate': session.config.baud_rate,
                'can_bitrate': session.config.can_bitrate,
            },
            'info': session.info,
            'connected_at': session.connected_at,
            'is_connected': self.is_connected(session.ecu_type)
        }
    
    def _get_protocol(self, ecu_type: Optional[ECUType] = None):
        """Get protocol instance for the specified or active ECU"""
        if ecu_type:
            return self.manager._protocols.get(ecu_type)
        else:
            return self.manager.get_active_protocol()


# Convenience functions for common operations
def quick_connect(ecu_type: ECUType, port: str, **kwargs) -> ECUBridge:
    """Quickly connect to an ECU with minimal configuration"""
    bridge = ECUBridge()
    
    # Default connection settings per ECU type
    defaults = {
        ECUType.BOSCH_ME17: {
            'connection_type': ConnectionType.SERIAL,
            'baud_rate': 38400
        },
        ECUType.SIEMENS_MSV: {
            'connection_type': ConnectionType.CAN_BUS,
            'can_bitrate': 500000
        },
        ECUType.DENSO_SH705X: {
            'connection_type': ConnectionType.SERIAL,
            'baud_rate': 19200
        }
    }
    
    # Build config
    ecu_defaults = defaults.get(ecu_type, {})
    ecu_defaults.update(kwargs)
    
    config = ECUConfig(
        ecu_type=ecu_type,
        port=port,
        **ecu_defaults
    )
    
    if bridge.configure_ecu(ecu_type, config):
        if bridge.connect(ecu_type):
            return bridge
    
    raise Exception(f"Failed to connect to {ecu_type.value}")


def auto_detect_ecu(ports: List[str]) -> Optional[ECUType]:
    """Attempt to auto-detect ECU type by trying connections"""
    logger.info("Starting ECU auto-detection...")
    
    ecu_types = [ECUType.BOSCH_ME17, ECUType.SIEMENS_MSV, ECUType.DENSO_SH705X]
    
    for port in ports:
        for ecu_type in ecu_types:
            try:
                logger.debug(f"Trying {ecu_type.value} on {port}")
                bridge = quick_connect(ecu_type, port)
                info = bridge.get_ecu_info()
                bridge.disconnect()
                
                if info and 'error' not in info:
                    logger.success(f"Detected {ecu_type.value} on {port}")
                    return ecu_type
                    
            except Exception as e:
                logger.debug(f"Failed to connect {ecu_type.value} on {port}: {str(e)}")
                continue
    
    logger.warning("No ECU detected on any port")
    return None