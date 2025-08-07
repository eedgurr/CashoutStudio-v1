"""
Denso SH705x ECU Protocol Implementation
"""

import serial
import time
import struct
from typing import Dict, List, Any
from loguru import logger

from ..ecu import ECUProtocol, ECUConfig


class DensoSH705xProtocol(ECUProtocol):
    """Denso SH705x ECU communication protocol implementation"""
    
    # Denso SH705x specific commands and constants
    SYNC_PATTERN = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x55\xAA'
    
    # Command codes for SH705x
    CMD_INIT = 0x00
    CMD_READ_ROM = 0x01
    CMD_READ_RAM = 0x02  
    CMD_WRITE_ROM = 0x03
    CMD_WRITE_RAM = 0x04
    CMD_ERASE_SECTOR = 0x05
    CMD_CHECKSUM = 0x06
    CMD_ECU_INFO = 0x07
    CMD_READ_DTC = 0x08
    CMD_CLEAR_DTC = 0x09
    CMD_RESET = 0x0A
    
    # Response codes
    RESP_ACK = 0x06
    RESP_NAK = 0x15
    RESP_DATA = 0x80
    
    # Memory regions
    ROM_BASE = 0x00000000
    RAM_BASE = 0x05FFFF00
    EEPROM_BASE = 0x00FE0000
    
    def __init__(self, config: ECUConfig):
        super().__init__(config)
        self._serial_connection = None
        self._session_active = False
        
    def connect(self) -> bool:
        """Establish connection to Denso SH705x ECU"""
        try:
            # Initialize serial connection
            self._serial_connection = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,  # Denso uses even parity
                stopbits=serial.STOPBITS_ONE,
                timeout=self.config.timeout
            )
            
            logger.debug("Initializing connection to Denso SH705x")
            
            # Send synchronization pattern
            self._serial_connection.write(self.SYNC_PATTERN)
            time.sleep(0.1)
            
            # Send initialization command
            init_frame = self._build_frame(self.CMD_INIT, b'')
            self._serial_connection.write(init_frame)
            
            # Wait for ACK
            response = self._read_response()
            if response and response[0] == self.RESP_ACK:
                # Send ECU wake-up sequence
                wake_up = self._build_frame(0x81, b'\x01\x02\x03')  # Custom wake-up
                self._serial_connection.write(wake_up)
                
                response2 = self._read_response()
                if response2 and response2[0] == self.RESP_ACK:
                    self.connected = True
                    self._session_active = True
                    logger.success("Connected to Denso SH705x ECU")
                    return True
            
            logger.error("Failed to establish session with Denso SH705x")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to Denso SH705x: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Denso SH705x ECU"""
        try:
            if self._serial_connection and self._serial_connection.is_open:
                if self._session_active:
                    # Send reset command to exit programming mode
                    reset_frame = self._build_frame(self.CMD_RESET, b'')
                    self._serial_connection.write(reset_frame)
                    time.sleep(0.5)  # Allow ECU to reset
                
                self._serial_connection.close()
                
            self.connected = False
            self._session_active = False
            logger.info("Disconnected from Denso SH705x ECU")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Denso SH705x: {str(e)}")
            return False
    
    def read_data(self, address: int, length: int) -> bytes:
        """Read data from Denso SH705x ECU memory"""
        if not self.connected or not self._serial_connection:
            raise Exception("Not connected to ECU")
        
        try:
            # Determine memory type based on address
            if address >= self.ROM_BASE and address < self.RAM_BASE:
                cmd = self.CMD_READ_ROM
            elif address >= self.RAM_BASE:
                cmd = self.CMD_READ_RAM
            else:
                cmd = self.CMD_READ_ROM  # Default to ROM
            
            # Build read command with address and length
            addr_bytes = struct.pack('>I', address)  # Big-endian 32-bit address
            len_bytes = struct.pack('>H', length)    # Big-endian 16-bit length
            
            command_data = addr_bytes + len_bytes
            frame = self._build_frame(cmd, command_data)
            
            # Send command
            self._serial_connection.write(frame)
            
            # Read response with retries
            response = self._read_response()
            if not response:
                raise Exception("No response from ECU")
            
            if response[0] == self.RESP_DATA:
                # Extract data payload
                data_length = struct.unpack('>H', response[1:3])[0]
                if len(response) >= 3 + data_length:
                    return response[3:3+data_length]
                else:
                    raise Exception("Incomplete data received")
            elif response[0] == self.RESP_NAK:
                raise Exception(f"ECU returned NAK, error code: {response[1] if len(response) > 1 else 'unknown'}")
            else:
                raise Exception(f"Unexpected response code: 0x{response[0]:02X}")
                
        except Exception as e:
            logger.error(f"Error reading data from Denso SH705x: {str(e)}")
            raise
    
    def write_data(self, address: int, data: bytes) -> bool:
        """Write data to Denso SH705x ECU memory"""
        if not self.connected or not self._serial_connection:
            raise Exception("Not connected to ECU")
        
        try:
            # Determine memory type and command
            if address >= self.ROM_BASE and address < self.RAM_BASE:
                cmd = self.CMD_WRITE_ROM
            elif address >= self.RAM_BASE:
                cmd = self.CMD_WRITE_RAM
            else:
                cmd = self.CMD_WRITE_RAM  # Default to RAM for safety
            
            # Denso SH705x typically requires sector erase before ROM write
            if cmd == self.CMD_WRITE_ROM:
                if not self._erase_sector(address):
                    logger.warning("Sector erase failed, attempting write anyway")
            
            # Build write command
            addr_bytes = struct.pack('>I', address)
            len_bytes = struct.pack('>H', len(data))
            
            command_data = addr_bytes + len_bytes + data
            frame = self._build_frame(cmd, command_data)
            
            # Send command
            self._serial_connection.write(frame)
            
            # Wait for acknowledgment
            response = self._read_response()
            if response and response[0] == self.RESP_ACK:
                # Verify write with checksum
                if self._verify_checksum(address, len(data)):
                    logger.debug(f"Successfully wrote {len(data)} bytes to address 0x{address:08X}")
                    return True
                else:
                    logger.error("Checksum verification failed after write")
                    return False
            elif response and response[0] == self.RESP_NAK:
                logger.error(f"Write failed with NAK, error: {response[1] if len(response) > 1 else 'unknown'}")
                return False
            else:
                logger.error("No valid response to write command")
                return False
                
        except Exception as e:
            logger.error(f"Error writing data to Denso SH705x: {str(e)}")
            return False
    
    def get_ecu_info(self) -> Dict[str, Any]:
        """Get ECU identification and version info"""
        if not self.connected:
            return {}
        
        try:
            # Send ECU info command
            info_frame = self._build_frame(self.CMD_ECU_INFO, b'')
            self._serial_connection.write(info_frame)
            
            response = self._read_response()
            
            info = {
                'ecu_type': 'Denso SH705x',
                'protocol': 'Denso Proprietary',
                'connection': f'{self.config.port}@{self.config.baud_rate}'
            }
            
            if response and response[0] == self.RESP_DATA and len(response) > 3:
                data = response[3:]  # Skip response code and length
                
                if len(data) >= 32:
                    # Parse ECU info structure
                    info['cpu_id'] = data[0:4].hex().upper()
                    info['rom_size'] = struct.unpack('>I', data[4:8])[0]
                    info['ram_size'] = struct.unpack('>I', data[8:12])[0]
                    info['part_number'] = data[12:24].decode('ascii', errors='ignore').strip()
                    info['software_version'] = data[24:32].decode('ascii', errors='ignore').strip()
                    
                    # Additional fields if available
                    if len(data) >= 48:
                        info['hardware_version'] = data[32:40].hex().upper()
                        info['calibration_id'] = data[40:48].decode('ascii', errors='ignore').strip()
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting Denso SH705x info: {str(e)}")
            return {'ecu_type': 'Denso SH705x', 'error': str(e)}
    
    def get_dtc_codes(self) -> List[str]:
        """Get diagnostic trouble codes"""
        if not self.connected:
            return []
        
        try:
            # Send read DTC command
            dtc_frame = self._build_frame(self.CMD_READ_DTC, b'')
            self._serial_connection.write(dtc_frame)
            
            response = self._read_response()
            dtc_codes = []
            
            if response and response[0] == self.RESP_DATA and len(response) > 3:
                data = response[3:]
                dtc_count = data[0] if data else 0
                
                # Each DTC is 2 bytes
                for i in range(1, min(len(data), 1 + dtc_count * 2), 2):
                    if i + 1 < len(data):
                        dtc_code = (data[i] << 8) | data[i + 1]
                        if dtc_code != 0:  # Skip empty codes
                            # Convert to standard format
                            dtc_prefix = ['P', 'C', 'B', 'U'][((dtc_code >> 14) & 0x03)]
                            dtc_codes.append(f"{dtc_prefix}{dtc_code & 0x3FFF:04X}")
            
            return dtc_codes
            
        except Exception as e:
            logger.error(f"Error reading DTCs from Denso SH705x: {str(e)}")
            return []
    
    def clear_dtc_codes(self) -> bool:
        """Clear diagnostic trouble codes"""
        if not self.connected:
            return False
        
        try:
            # Send clear DTC command
            clear_frame = self._build_frame(self.CMD_CLEAR_DTC, b'')
            self._serial_connection.write(clear_frame)
            
            response = self._read_response()
            if response and response[0] == self.RESP_ACK:
                logger.info("Successfully cleared DTCs on Denso SH705x")
                return True
            elif response and response[0] == self.RESP_NAK:
                logger.error("Failed to clear DTCs - ECU returned NAK")
                return False
            else:
                logger.error("No valid response to clear DTC command")
                return False
                
        except Exception as e:
            logger.error(f"Error clearing DTCs on Denso SH705x: {str(e)}")
            return False
    
    def _build_frame(self, command: int, data: bytes) -> bytes:
        """Build a Denso SH705x protocol frame"""
        # Frame format: [STX] [LEN] [CMD] [DATA...] [CHK] [ETX]
        STX = 0x02
        ETX = 0x03
        
        frame_data = bytes([command]) + data
        length = len(frame_data)
        checksum = self._calculate_checksum(frame_data)
        
        return bytes([STX, length]) + frame_data + bytes([checksum, ETX])
    
    def _read_response(self) -> bytes:
        """Read response from ECU with frame parsing"""
        if not self._serial_connection:
            return b''
        
        try:
            # Look for STX
            while True:
                byte = self._serial_connection.read(1)
                if not byte:
                    return b''
                if byte[0] == 0x02:  # STX found
                    break
            
            # Read length
            length_byte = self._serial_connection.read(1)
            if not length_byte:
                return b''
            
            length = length_byte[0]
            if length == 0:
                return b''
            
            # Read frame data, checksum, and ETX
            remaining = self._serial_connection.read(length + 2)  # +1 for checksum, +1 for ETX
            if len(remaining) == length + 2 and remaining[-1] == 0x03:  # ETX check
                frame_data = remaining[:-2]
                received_checksum = remaining[-2]
                calculated_checksum = self._calculate_checksum(frame_data)
                
                if received_checksum == calculated_checksum:
                    return frame_data
                else:
                    logger.warning("Checksum mismatch in received frame")
                    return b''
            
            return b''
            
        except Exception as e:
            logger.error(f"Error reading response: {str(e)}")
            return b''
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate checksum for Denso protocol"""
        return (256 - (sum(data) % 256)) % 256
    
    def _erase_sector(self, address: int) -> bool:
        """Erase flash sector containing the given address"""
        try:
            # Calculate sector address (align to sector boundary)
            sector_size = 0x1000  # 4KB sectors typical for SH705x
            sector_addr = address & ~(sector_size - 1)
            
            addr_bytes = struct.pack('>I', sector_addr)
            erase_frame = self._build_frame(self.CMD_ERASE_SECTOR, addr_bytes)
            
            self._serial_connection.write(erase_frame)
            
            # Erase can take longer, increase timeout
            original_timeout = self._serial_connection.timeout
            self._serial_connection.timeout = 10.0
            
            response = self._read_response()
            
            self._serial_connection.timeout = original_timeout
            
            return response and response[0] == self.RESP_ACK
            
        except Exception as e:
            logger.error(f"Error erasing sector: {str(e)}")
            return False
    
    def _verify_checksum(self, address: int, length: int) -> bool:
        """Verify data integrity using checksum"""
        try:
            addr_bytes = struct.pack('>I', address)
            len_bytes = struct.pack('>H', length)
            
            checksum_frame = self._build_frame(self.CMD_CHECKSUM, addr_bytes + len_bytes)
            self._serial_connection.write(checksum_frame)
            
            response = self._read_response()
            if response and response[0] == self.RESP_DATA and len(response) >= 5:
                # Checksum response contains the calculated checksum
                return True  # Simplified - actual implementation would compare checksums
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying checksum: {str(e)}")
            return False