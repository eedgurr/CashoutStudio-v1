"""
Siemens MSV ECU Protocol Implementation
"""

import serial
import can
import time
from typing import Dict, List, Any
from loguru import logger

from ..ecu import ECUProtocol, ECUConfig, ConnectionType


class SiemensMSVProtocol(ECUProtocol):
    """Siemens MSV ECU communication protocol implementation"""
    
    # Siemens MSV specific CAN IDs and commands
    REQUEST_ID = 0x7E0
    RESPONSE_ID = 0x7E8
    
    # UDS (ISO 14229) commands for MSV
    CMD_DIAGNOSTIC_SESSION = 0x10
    CMD_READ_DATA = 0x22
    CMD_WRITE_DATA = 0x2E
    CMD_ROUTINE_CONTROL = 0x31
    CMD_READ_DTC = 0x19
    CMD_CLEAR_DTC = 0x14
    CMD_ECU_RESET = 0x11
    
    # Session types
    SESSION_DEFAULT = 0x01
    SESSION_PROGRAMMING = 0x02
    SESSION_EXTENDED = 0x03
    
    def __init__(self, config: ECUConfig):
        super().__init__(config)
        self._can_bus = None
        self._sequence_number = 0x21
        
    def connect(self) -> bool:
        """Establish connection to Siemens MSV ECU"""
        try:
            if self.config.connection_type == ConnectionType.CAN_BUS:
                return self._connect_can()
            elif self.config.connection_type == ConnectionType.SERIAL:
                return self._connect_serial()
            else:
                logger.error(f"Unsupported connection type: {self.config.connection_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Siemens MSV: {str(e)}")
            return False
    
    def _connect_can(self) -> bool:
        """Connect via CAN bus"""
        try:
            # Initialize CAN bus connection
            self._can_bus = can.interface.Bus(
                interface='socketcan',
                channel=self.config.port,
                bitrate=self.config.can_bitrate
            )
            
            logger.debug("Sending diagnostic session control to Siemens MSV")
            
            # Send diagnostic session control (extended session)
            session_msg = can.Message(
                arbitration_id=self.REQUEST_ID,
                data=[0x02, self.CMD_DIAGNOSTIC_SESSION, self.SESSION_EXTENDED],
                is_extended_id=False
            )
            
            self._can_bus.send(session_msg)
            
            # Wait for positive response
            response = self._can_bus.recv(timeout=self.config.timeout)
            if response and response.arbitration_id == self.RESPONSE_ID:
                if len(response.data) >= 2 and response.data[1] == 0x50:  # Positive response
                    self.connected = True
                    logger.success("Connected to Siemens MSV ECU via CAN")
                    return True
            
            logger.error("Failed to establish session with Siemens MSV")
            return False
            
        except Exception as e:
            logger.error(f"CAN connection error: {str(e)}")
            return False
    
    def _connect_serial(self) -> bool:
        """Connect via serial (K-Line simulation)"""
        try:
            # Initialize serial connection for K-Line
            self._serial_connection = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.config.timeout
            )
            
            # Send wake-up and session establishment
            wake_up = b'\x00' * 5 + b'\x55' + b'\x8A' + b'\x08'
            self._serial_connection.write(wake_up)
            time.sleep(0.05)
            
            # Send session control
            session_cmd = bytes([0x02, self.CMD_DIAGNOSTIC_SESSION, self.SESSION_EXTENDED])
            checksum = self._calculate_checksum(session_cmd)
            frame = session_cmd + bytes([checksum])
            
            self._serial_connection.write(frame)
            
            # Read response
            response = self._serial_connection.read(10)
            if response and len(response) >= 3 and response[1] == 0x50:
                self.connected = True
                logger.success("Connected to Siemens MSV ECU via Serial")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Serial connection error: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Siemens MSV ECU"""
        try:
            if self._can_bus:
                # Send default session before disconnecting
                default_session = can.Message(
                    arbitration_id=self.REQUEST_ID,
                    data=[0x02, self.CMD_DIAGNOSTIC_SESSION, self.SESSION_DEFAULT]
                )
                self._can_bus.send(default_session)
                time.sleep(0.1)
                
                self._can_bus.shutdown()
                self._can_bus = None
            
            if hasattr(self, '_serial_connection') and self._serial_connection:
                self._serial_connection.close()
            
            self.connected = False
            logger.info("Disconnected from Siemens MSV ECU")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Siemens MSV: {str(e)}")
            return False
    
    def read_data(self, address: int, length: int) -> bytes:
        """Read data from Siemens MSV ECU memory"""
        if not self.connected:
            raise Exception("Not connected to ECU")
        
        try:
            if self._can_bus:
                return self._read_data_can(address, length)
            else:
                return self._read_data_serial(address, length)
                
        except Exception as e:
            logger.error(f"Error reading data from Siemens MSV: {str(e)}")
            raise
    
    def _read_data_can(self, address: int, length: int) -> bytes:
        """Read data via CAN"""
        # Siemens MSV uses data identifier based reading
        data_id = (address >> 8) & 0xFFFF  # Convert address to data identifier
        
        read_msg = can.Message(
            arbitration_id=self.REQUEST_ID,
            data=[0x03, self.CMD_READ_DATA, (data_id >> 8) & 0xFF, data_id & 0xFF]
        )
        
        self._can_bus.send(read_msg)
        
        # Handle multi-frame response
        response_data = b''
        while len(response_data) < length:
            response = self._can_bus.recv(timeout=self.config.timeout)
            if not response or response.arbitration_id != self.RESPONSE_ID:
                raise Exception("Invalid or missing response")
            
            if response.data[0] & 0xF0 == 0x10:  # First frame
                data_length = ((response.data[0] & 0x0F) << 8) | response.data[1]
                response_data += response.data[4:]  # Skip service ID and data ID
                
                # Send flow control
                flow_control = can.Message(
                    arbitration_id=self.REQUEST_ID,
                    data=[0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
                )
                self._can_bus.send(flow_control)
                
            elif response.data[0] & 0xF0 == 0x20:  # Consecutive frame
                response_data += response.data[1:]
            else:  # Single frame
                response_data = response.data[3:]  # Skip length and service ID
                break
        
        return response_data[:length]
    
    def _read_data_serial(self, address: int, length: int) -> bytes:
        """Read data via serial"""
        # Construct read data command
        data_id = (address >> 8) & 0xFFFF
        command = bytes([0x03, self.CMD_READ_DATA, (data_id >> 8) & 0xFF, data_id & 0xFF])
        checksum = self._calculate_checksum(command)
        frame = command + bytes([checksum])
        
        self._serial_connection.write(frame)
        
        # Read response
        response = self._serial_connection.read(256)  # Max response size
        if response and len(response) >= 4:
            return response[3:-1]  # Skip header and checksum
        
        raise Exception("No valid response received")
    
    def write_data(self, address: int, data: bytes) -> bool:
        """Write data to Siemens MSV ECU memory"""
        if not self.connected:
            raise Exception("Not connected to ECU")
        
        try:
            data_id = (address >> 8) & 0xFFFF
            
            if self._can_bus:
                # Multi-frame write if data is large
                if len(data) <= 3:  # Single frame
                    write_msg = can.Message(
                        arbitration_id=self.REQUEST_ID,
                        data=[len(data) + 3, self.CMD_WRITE_DATA, (data_id >> 8) & 0xFF, data_id & 0xFF] + list(data)
                    )
                    self._can_bus.send(write_msg)
                else:
                    # Multi-frame implementation would go here
                    pass
                
                # Wait for positive response
                response = self._can_bus.recv(timeout=self.config.timeout)
                if response and response.arbitration_id == self.RESPONSE_ID:
                    if len(response.data) >= 2 and response.data[1] == 0x6E:  # Positive response
                        return True
                
                return False
            
            else:  # Serial
                command = bytes([len(data) + 3, self.CMD_WRITE_DATA, (data_id >> 8) & 0xFF, data_id & 0xFF]) + data
                checksum = self._calculate_checksum(command)
                frame = command + bytes([checksum])
                
                self._serial_connection.write(frame)
                
                response = self._serial_connection.read(10)
                return response and len(response) >= 2 and response[1] == 0x6E
                
        except Exception as e:
            logger.error(f"Error writing data to Siemens MSV: {str(e)}")
            return False
    
    def get_ecu_info(self) -> Dict[str, Any]:
        """Get ECU identification and version info"""
        if not self.connected:
            return {}
        
        try:
            info = {
                'ecu_type': 'Siemens MSV',
                'protocol': 'UDS/ISO14229',
                'connection': f'{self.config.port}@{self.config.can_bitrate if self._can_bus else self.config.baud_rate}'
            }
            
            # Read ECU identification (DID 0xF186 - Active Diagnostic Session)
            try:
                session_info = self.read_data(0xF186 << 8, 16)
                if session_info:
                    info['active_session'] = session_info.hex()
            except:
                pass
            
            # Read software version (DID 0xF189)
            try:
                sw_version = self.read_data(0xF189 << 8, 16)
                if sw_version:
                    info['software_version'] = sw_version.decode('ascii', errors='ignore')
            except:
                pass
            
            # Read part number (DID 0xF187)
            try:
                part_number = self.read_data(0xF187 << 8, 16)
                if part_number:
                    info['part_number'] = part_number.decode('ascii', errors='ignore')
            except:
                pass
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting Siemens MSV info: {str(e)}")
            return {'ecu_type': 'Siemens MSV', 'error': str(e)}
    
    def get_dtc_codes(self) -> List[str]:
        """Get diagnostic trouble codes"""
        if not self.connected:
            return []
        
        try:
            dtc_codes = []
            
            if self._can_bus:
                # Read DTCs by status (0x02 = confirmed DTCs)
                dtc_msg = can.Message(
                    arbitration_id=self.REQUEST_ID,
                    data=[0x02, self.CMD_READ_DTC, 0x02]
                )
                self._can_bus.send(dtc_msg)
                
                response = self._can_bus.recv(timeout=self.config.timeout)
                if response and response.arbitration_id == self.RESPONSE_ID:
                    if len(response.data) >= 2 and response.data[1] == 0x59:
                        # Parse DTC data (each DTC is 3 bytes)
                        dtc_data = response.data[3:]
                        for i in range(0, len(dtc_data), 3):
                            if i + 2 < len(dtc_data):
                                dtc_high = dtc_data[i]
                                dtc_low = (dtc_data[i+1] << 8) | dtc_data[i+2]
                                dtc_code = f"P{dtc_high:02X}{dtc_low:04X}"
                                dtc_codes.append(dtc_code)
            
            return dtc_codes
            
        except Exception as e:
            logger.error(f"Error reading DTCs from Siemens MSV: {str(e)}")
            return []
    
    def clear_dtc_codes(self) -> bool:
        """Clear diagnostic trouble codes"""
        if not self.connected:
            return False
        
        try:
            if self._can_bus:
                # Clear all DTCs (group 0xFFFFFF)
                clear_msg = can.Message(
                    arbitration_id=self.REQUEST_ID,
                    data=[0x04, self.CMD_CLEAR_DTC, 0xFF, 0xFF, 0xFF]
                )
                self._can_bus.send(clear_msg)
                
                response = self._can_bus.recv(timeout=self.config.timeout)
                if response and response.arbitration_id == self.RESPONSE_ID:
                    if len(response.data) >= 2 and response.data[1] == 0x54:  # Positive response
                        logger.info("Successfully cleared DTCs on Siemens MSV")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error clearing DTCs on Siemens MSV: {str(e)}")
            return False
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate checksum for serial communication"""
        return (256 - (sum(data) % 256)) % 256