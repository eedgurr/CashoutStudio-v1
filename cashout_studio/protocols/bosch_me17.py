"""
Bosch ME17 ECU Protocol Implementation
"""

import serial
import time
from typing import Dict, List, Any
from loguru import logger

from ..ecu import ECUProtocol, ECUConfig


class BoschME17Protocol(ECUProtocol):
    """Bosch ME17 ECU communication protocol implementation"""
    
    # Bosch ME17 specific commands and constants
    CMD_CONNECT = b'\x81'
    CMD_DISCONNECT = b'\x82'  
    CMD_READ_MEMORY = b'\x23'
    CMD_WRITE_MEMORY = b'\x3D'
    CMD_READ_ID = b'\x1A'
    CMD_READ_DTC = b'\x19\x02'
    CMD_CLEAR_DTC = b'\x14\xFF\x00'
    
    RESPONSE_OK = b'\x50'
    RESPONSE_ERROR = b'\x7F'
    
    def __init__(self, config: ECUConfig):
        super().__init__(config)
        self._serial_connection = None
        
    def connect(self) -> bool:
        """Establish connection to Bosch ME17 ECU"""
        try:
            # Initialize serial connection
            self._serial_connection = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.config.timeout
            )
            
            # Send connection sequence
            logger.debug("Sending connection sequence to Bosch ME17")
            
            # Send wake-up pattern
            wake_up = b'\x00' * 10 + b'\x55' + b'\x01' + b'\x8A'
            self._serial_connection.write(wake_up)
            time.sleep(0.1)
            
            # Send connect command
            connect_frame = self._build_kwp2000_frame(self.CMD_CONNECT)
            self._serial_connection.write(connect_frame)
            
            # Wait for response
            response = self._read_response()
            if response and self.RESPONSE_OK in response:
                self.connected = True
                logger.success("Connected to Bosch ME17 ECU")
                return True
            else:
                logger.error("Failed to connect to Bosch ME17 ECU")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Bosch ME17: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Bosch ME17 ECU"""
        try:
            if self._serial_connection and self._serial_connection.is_open:
                # Send disconnect command
                disconnect_frame = self._build_kwp2000_frame(self.CMD_DISCONNECT)
                self._serial_connection.write(disconnect_frame)
                time.sleep(0.1)
                
                self._serial_connection.close()
                
            self.connected = False
            logger.info("Disconnected from Bosch ME17 ECU")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Bosch ME17: {str(e)}")
            return False
    
    def read_data(self, address: int, length: int) -> bytes:
        """Read data from Bosch ME17 ECU memory"""
        if not self.connected or not self._serial_connection:
            raise Exception("Not connected to ECU")
        
        try:
            # Build read memory command
            addr_bytes = address.to_bytes(3, 'big')  # ME17 uses 24-bit addressing
            len_bytes = length.to_bytes(2, 'big')    # 16-bit length
            
            command = self.CMD_READ_MEMORY + addr_bytes + len_bytes
            frame = self._build_kwp2000_frame(command)
            
            # Send command and read response
            self._serial_connection.write(frame)
            response = self._read_response()
            
            if response and len(response) > 2:
                # Extract data from response (skip header)
                return response[2:]
            else:
                raise Exception("Invalid response from ECU")
                
        except Exception as e:
            logger.error(f"Error reading data from Bosch ME17: {str(e)}")
            raise
    
    def write_data(self, address: int, data: bytes) -> bool:
        """Write data to Bosch ME17 ECU memory"""
        if not self.connected or not self._serial_connection:
            raise Exception("Not connected to ECU")
        
        try:
            # Build write memory command
            addr_bytes = address.to_bytes(3, 'big')
            command = self.CMD_WRITE_MEMORY + addr_bytes + data
            frame = self._build_kwp2000_frame(command)
            
            # Send command and check response
            self._serial_connection.write(frame)
            response = self._read_response()
            
            if response and self.RESPONSE_OK in response:
                logger.debug(f"Successfully wrote {len(data)} bytes to address 0x{address:06X}")
                return True
            else:
                logger.error("Write command failed")
                return False
                
        except Exception as e:
            logger.error(f"Error writing data to Bosch ME17: {str(e)}")
            return False
    
    def get_ecu_info(self) -> Dict[str, Any]:
        """Get ECU identification and version info"""
        if not self.connected:
            return {}
        
        try:
            # Send read identification command
            id_frame = self._build_kwp2000_frame(self.CMD_READ_ID + b'\x86')
            self._serial_connection.write(id_frame)
            response = self._read_response()
            
            info = {
                'ecu_type': 'Bosch ME17',
                'protocol': 'KWP2000',
                'connection': f'{self.config.port}@{self.config.baud_rate}'
            }
            
            if response and len(response) > 2:
                # Parse ECU identification data
                data = response[2:]
                if len(data) >= 20:
                    info['part_number'] = data[0:10].hex()
                    info['sw_version'] = data[10:14].hex()  
                    info['hw_version'] = data[14:18].hex()
                    info['supplier_id'] = data[18:20].hex()
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting Bosch ME17 info: {str(e)}")
            return {'ecu_type': 'Bosch ME17', 'error': str(e)}
    
    def get_dtc_codes(self) -> List[str]:
        """Get diagnostic trouble codes"""
        if not self.connected:
            return []
        
        try:
            # Send read DTC command
            dtc_frame = self._build_kwp2000_frame(self.CMD_READ_DTC)
            self._serial_connection.write(dtc_frame)
            response = self._read_response()
            
            dtc_codes = []
            if response and len(response) > 2:
                data = response[2:]
                # Parse DTC codes (each DTC is 2 bytes)
                for i in range(0, len(data), 2):
                    if i + 1 < len(data):
                        dtc_code = (data[i] << 8) | data[i + 1]
                        if dtc_code != 0:  # Skip empty codes
                            dtc_codes.append(f"P{dtc_code:04X}")
            
            return dtc_codes
            
        except Exception as e:
            logger.error(f"Error reading DTCs from Bosch ME17: {str(e)}")
            return []
    
    def clear_dtc_codes(self) -> bool:
        """Clear diagnostic trouble codes"""
        if not self.connected:
            return False
        
        try:
            # Send clear DTC command
            clear_frame = self._build_kwp2000_frame(self.CMD_CLEAR_DTC)
            self._serial_connection.write(clear_frame)
            response = self._read_response()
            
            if response and self.RESPONSE_OK in response:
                logger.info("Successfully cleared DTCs on Bosch ME17")
                return True
            else:
                logger.error("Failed to clear DTCs on Bosch ME17")
                return False
                
        except Exception as e:
            logger.error(f"Error clearing DTCs on Bosch ME17: {str(e)}")
            return False
    
    def _build_kwp2000_frame(self, data: bytes) -> bytes:
        """Build a KWP2000 protocol frame"""
        # Simple KWP2000 frame: [Length] [Data] [Checksum]
        length = len(data)
        checksum = (sum(data) + length) & 0xFF
        return bytes([length]) + data + bytes([checksum])
    
    def _read_response(self) -> bytes:
        """Read response from ECU"""
        if not self._serial_connection:
            return b''
        
        try:
            # Read length byte first
            length_byte = self._serial_connection.read(1)
            if not length_byte:
                return b''
            
            length = length_byte[0]
            if length == 0:
                return b''
            
            # Read data and checksum
            remaining = self._serial_connection.read(length + 1)  # +1 for checksum
            if len(remaining) == length + 1:
                return length_byte + remaining
            else:
                logger.warning("Incomplete response received")
                return b''
                
        except Exception as e:
            logger.error(f"Error reading response: {str(e)}")
            return b''