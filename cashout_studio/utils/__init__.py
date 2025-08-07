"""
Utility functions for ECU operations
"""

import struct
from typing import Dict, Any, List
from loguru import logger


def hex_dump(data: bytes, address: int = 0, width: int = 16) -> str:
    """Generate a hex dump of binary data"""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_data = ' '.join(f'{b:02X}' for b in chunk)
        ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        lines.append(f"{address+i:08X}: {hex_data:<48} {ascii_data}")
    return '\n'.join(lines)


def parse_dtc_code(code: int, format_type: str = "standard") -> str:
    """Parse DTC code to standard format"""
    if format_type == "standard":
        # Standard OBD-II format
        prefixes = ['P', 'C', 'B', 'U']
        prefix = prefixes[(code >> 14) & 0x03]
        return f"{prefix}{code & 0x3FFF:04X}"
    elif format_type == "bosch":
        # Bosch specific format
        return f"P{code:04X}"
    elif format_type == "denso":
        # Denso specific format  
        prefixes = ['P', 'C', 'B', 'U']
        prefix = prefixes[(code >> 14) & 0x03]
        return f"{prefix}{code & 0x3FFF:04X}"
    else:
        return f"{code:04X}"


def calculate_checksum(data: bytes, algorithm: str = "sum") -> int:
    """Calculate checksum using various algorithms"""
    if algorithm == "sum":
        return sum(data) & 0xFF
    elif algorithm == "xor":
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum
    elif algorithm == "sum_complement":
        return (256 - (sum(data) % 256)) % 256
    elif algorithm == "crc8":
        # Simple CRC-8
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x07
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc
    else:
        raise ValueError(f"Unknown checksum algorithm: {algorithm}")


def validate_address_range(address: int, length: int, valid_ranges: List[tuple]) -> bool:
    """Validate if address range is within allowed memory regions"""
    end_address = address + length - 1
    
    for start, end in valid_ranges:
        if start <= address <= end and start <= end_address <= end:
            return True
    
    return False


def format_memory_size(size_bytes: int) -> str:
    """Format memory size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def extract_ascii_string(data: bytes, offset: int = 0, max_length: int = None) -> str:
    """Extract ASCII string from binary data"""
    start = offset
    end = offset + max_length if max_length else len(data)
    
    # Find null terminator
    for i in range(start, min(end, len(data))):
        if data[i] == 0:
            end = i
            break
    
    # Extract and decode
    string_data = data[start:end]
    return string_data.decode('ascii', errors='ignore').strip()


def parse_version_string(version_data: bytes) -> Dict[str, Any]:
    """Parse version information from binary data"""
    version_info = {}
    
    if len(version_data) >= 4:
        # Try to parse as major.minor.patch.build
        try:
            version_info['major'] = version_data[0]
            version_info['minor'] = version_data[1] 
            version_info['patch'] = version_data[2]
            version_info['build'] = version_data[3]
            version_info['string'] = f"{version_data[0]}.{version_data[1]}.{version_data[2]}.{version_data[3]}"
        except:
            version_info['raw'] = version_data.hex()
    else:
        version_info['raw'] = version_data.hex()
    
    return version_info


def create_memory_map(ranges: List[Dict[str, Any]]) -> str:
    """Create a textual memory map representation"""
    lines = ["Memory Map:"]
    lines.append("-" * 50)
    
    for region in sorted(ranges, key=lambda x: x['start']):
        start = region['start']
        end = region.get('end', start + region.get('size', 0) - 1)
        name = region.get('name', 'Unknown')
        access = region.get('access', 'RW')
        
        lines.append(f"0x{start:08X} - 0x{end:08X} : {name} ({access})")
    
    return '\n'.join(lines)


def analyze_ecu_data(data: bytes) -> Dict[str, Any]:
    """Analyze ECU data and extract useful information"""
    analysis = {
        'size': len(data),
        'size_formatted': format_memory_size(len(data)),
        'checksums': {},
        'patterns': [],
        'strings': []
    }
    
    # Calculate various checksums
    try:
        analysis['checksums']['sum'] = calculate_checksum(data, 'sum')
        analysis['checksums']['xor'] = calculate_checksum(data, 'xor')
        analysis['checksums']['sum_complement'] = calculate_checksum(data, 'sum_complement')
        analysis['checksums']['crc8'] = calculate_checksum(data, 'crc8')
    except Exception as e:
        logger.debug(f"Error calculating checksums: {e}")
    
    # Find ASCII strings
    current_string = b''
    for i, byte in enumerate(data):
        if 32 <= byte <= 126:  # Printable ASCII
            current_string += bytes([byte])
        else:
            if len(current_string) >= 4:  # Minimum string length
                analysis['strings'].append({
                    'offset': i - len(current_string),
                    'length': len(current_string),
                    'text': current_string.decode('ascii')
                })
            current_string = b''
    
    # Add final string if exists
    if len(current_string) >= 4:
        analysis['strings'].append({
            'offset': len(data) - len(current_string),
            'length': len(current_string),
            'text': current_string.decode('ascii')
        })
    
    # Look for common patterns
    patterns_to_find = [
        (b'\xFF\xFF\xFF\xFF', 'Empty/Erased'),
        (b'\x00\x00\x00\x00', 'Zero-filled'),
        (b'ECU', 'ECU identifier'),
        (b'BOOT', 'Bootloader'),
        (b'CAL', 'Calibration'),
        (b'VIN', 'VIN identifier'),
    ]
    
    for pattern, description in patterns_to_find:
        offset = data.find(pattern)
        if offset != -1:
            analysis['patterns'].append({
                'pattern': pattern.hex(),
                'description': description,
                'offset': offset,
                'count': data.count(pattern)
            })
    
    return analysis


class ECUMemoryRegion:
    """Represents a memory region in an ECU"""
    
    def __init__(self, name: str, start: int, size: int, access: str = "RW", description: str = ""):
        self.name = name
        self.start = start
        self.size = size
        self.end = start + size - 1
        self.access = access
        self.description = description
    
    def contains(self, address: int) -> bool:
        """Check if address is within this region"""
        return self.start <= address <= self.end
    
    def __str__(self) -> str:
        return f"{self.name}: 0x{self.start:08X}-0x{self.end:08X} ({format_memory_size(self.size)}, {self.access})"


# Common ECU memory layouts
BOSCH_ME17_MEMORY_MAP = [
    ECUMemoryRegion("Internal Flash", 0x00000000, 0x200000, "RW", "Main program storage"),
    ECUMemoryRegion("External Flash", 0x00200000, 0x400000, "RW", "Calibration data"),
    ECUMemoryRegion("RAM", 0x50000000, 0x40000, "RW", "Runtime variables"),
    ECUMemoryRegion("Boot ROM", 0x1FFF0000, 0x10000, "R", "Boot loader"),
]

SIEMENS_MSV_MEMORY_MAP = [
    ECUMemoryRegion("Flash Bank 1", 0x00000000, 0x100000, "RW", "Program code"),
    ECUMemoryRegion("Flash Bank 2", 0x00100000, 0x100000, "RW", "Calibration"),
    ECUMemoryRegion("RAM", 0x40000000, 0x20000, "RW", "Working memory"),
    ECUMemoryRegion("EEPROM", 0x08000000, 0x4000, "RW", "Configuration data"),
]

DENSO_SH705X_MEMORY_MAP = [
    ECUMemoryRegion("ROM", 0x00000000, 0x80000, "RW", "Program ROM"),
    ECUMemoryRegion("RAM", 0x05FFFF00, 0x4000, "RW", "System RAM"),
    ECUMemoryRegion("EEPROM", 0x00FE0000, 0x2000, "RW", "Data EEPROM"),
    ECUMemoryRegion("I/O", 0x05FFE000, 0x1000, "RW", "I/O registers"),
]