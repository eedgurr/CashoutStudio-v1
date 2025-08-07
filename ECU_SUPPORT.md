# CashoutStudio-v1 ECU Support

## Overview

CashoutStudio-v1 is an offline AI tuning canvas with Web3 signatures that provides comprehensive ECU (Engine Control Unit) support for automotive tuning applications. The system includes a Python-based bridge layer that enables seamless communication with multiple ECU brands and protocols.

## Supported ECU Types

### Bosch ME17
- **Protocol**: KWP2000 over K-Line
- **Connection**: Serial (RS232/USB)
- **Baud Rates**: 38400 (default), 57600
- **Features**: Memory read/write, DTC handling, ECU identification
- **Memory Layout**: 24-bit addressing, Internal/External Flash support

### Siemens MSV
- **Protocol**: UDS (ISO 14229) 
- **Connection**: CAN Bus or K-Line
- **CAN Settings**: 500kbps (default), ID 0x7E0/0x7E8
- **Features**: Multi-frame messaging, diagnostic sessions, routine control
- **Memory Layout**: Data identifier based access

### Denso SH705x
- **Protocol**: Proprietary Denso protocol
- **Connection**: Serial (RS232/USB) 
- **Baud Rates**: 19200 (default), 38400
- **Features**: ROM/RAM/EEPROM access, sector erase, checksum verification
- **Memory Layout**: 32-bit addressing, multiple memory regions

## Installation

### Prerequisites

```bash
# Install required system packages (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3-dev python3-pip can-utils

# For CAN bus support
sudo modprobe can
sudo modprobe can_raw
```

### Python Package Installation

```bash
# Install from source
git clone https://github.com/eedgurr/CashoutStudio-v1.git
cd CashoutStudio-v1
pip install -e .

# Or install requirements directly
pip install -r requirements.txt
```

### Hardware Setup

#### Serial Connections (K-Line/RS232)
- Connect ECU K-Line to USB-Serial adapter
- Ensure proper ground connection
- Use appropriate voltage levels (12V automotive to 5V/3.3V logic)

#### CAN Bus Connections
- Connect to vehicle's CAN bus via OBD-II port or direct ECU access
- Use CAN transceiver (MCP2515, etc.) with Raspberry Pi/Linux system
- Configure CAN interface: `sudo ip link set can0 up type can bitrate 500000`

## Quick Start

### Basic Connection Example

```python
from cashout_studio.bridge import quick_connect
from cashout_studio.ecu import ECUType

# Connect to Bosch ME17 ECU
bridge = quick_connect(ECUType.BOSCH_ME17, "/dev/ttyUSB0")

# Get ECU information
info = bridge.get_ecu_info()
print(f"Connected to: {info['ecu_type']}")
print(f"Part Number: {info.get('part_number', 'Unknown')}")

# Read diagnostic codes
dtc_codes = bridge.get_diagnostic_codes()
print(f"DTC Codes: {dtc_codes}")

# Clean disconnect
bridge.disconnect()
```

### Memory Operations

```python
# Read ECU memory
address = 0x00001000
length = 256
data = bridge.read_memory(address, length)

# Write to ECU memory (use with caution!)
bridge.write_memory(address, b'\x01\x02\x03\x04')
```

### Command Line Interface

```bash
# List supported ECU types
cashout-studio list

# Connect to ECU and show info
cashout-studio connect bosch_me17 /dev/ttyUSB0 --read-dtc

# Auto-detect ECU type
cashout-studio detect --ports /dev/ttyUSB0 /dev/ttyUSB1 can0

# Read memory
cashout-studio read bosch_me17 /dev/ttyUSB0 0x1000 256 -o dump.bin

# Write memory from file
cashout-studio write denso_sh705x /dev/ttyUSB1 0x50000000 --file data.bin

# Clear diagnostic codes
cashout-studio clear-dtc siemens_msv can0
```

## Architecture

### ECU Bridge Layer
The bridge layer provides a unified interface for all ECU communications:

```python
from cashout_studio.bridge import ECUBridge
from cashout_studio.ecu import ECUType, ECUConfig, ConnectionType

bridge = ECUBridge()

# Configure multiple ECU types
config = ECUConfig(
    ecu_type=ECUType.BOSCH_ME17,
    connection_type=ConnectionType.SERIAL,
    port="/dev/ttyUSB0",
    baud_rate=38400,
    timeout=5.0
)

bridge.configure_ecu(ECUType.BOSCH_ME17, config)
bridge.connect(ECUType.BOSCH_ME17)
```

### Protocol Implementations
Each ECU type has its own protocol implementation:

- `BoschME17Protocol`: KWP2000 protocol handler
- `SiemensMSVProtocol`: UDS/ISO14229 protocol handler  
- `DensoSH705xProtocol`: Proprietary Denso protocol handler

### Configuration Management
Persistent configuration storage for ECU profiles:

```python
from cashout_studio.config import get_config_manager

config_manager = get_config_manager()

# List available profiles
profiles = config_manager.list_profiles()

# Get specific profile
profile = config_manager.get_profile('Bosch_ME17_Serial')

# Create custom profile
custom_profile = ECUProfile(
    name="My_Custom_ECU",
    ecu_type=ECUType.BOSCH_ME17,
    config=custom_config,
    description="Custom configuration"
)
config_manager.add_profile(custom_profile)
```

## Protocol Details

### Bosch ME17 (KWP2000)

**Connection Sequence:**
1. Send wake-up pattern: `00 00 00 00 00 00 00 00 00 00 55 01 8A`
2. Send connect command: `81`
3. Wait for positive response: `50`

**Memory Access:**
- Read: `23 [addr:3] [len:2]`
- Write: `3D [addr:3] [data:n]`
- Response: `50` (success) or `7F` (error)

**Frame Format:** `[Length] [Data] [Checksum]`

### Siemens MSV (UDS/ISO 14229)

**CAN IDs:**
- Request: 0x7E0
- Response: 0x7E8

**Services:**
- Diagnostic Session Control: `10 [session_type]`
- Read Data by Identifier: `22 [DID:2]`
- Write Data by Identifier: `2E [DID:2] [data:n]`
- Read DTC Information: `19 [sub_function]`

**Multi-Frame Handling:**
- Single Frame: `0N [data]` (N = length)
- First Frame: `1N LL [data]` (N+LL*256 = length)
- Consecutive Frame: `2N [data]` (N = sequence)
- Flow Control: `30 00 00`

### Denso SH705x (Proprietary)

**Frame Format:** `[STX] [LEN] [CMD] [DATA] [CHK] [ETX]`
- STX: 0x02
- ETX: 0x03
- Checksum: Two's complement

**Commands:**
- Initialize: 0x00
- Read ROM: 0x01
- Read RAM: 0x02
- Write ROM: 0x03 (requires sector erase)
- Write RAM: 0x04
- Erase Sector: 0x05

**Memory Regions:**
- ROM: 0x00000000 - 0x0007FFFF
- RAM: 0x05FFFF00 - 0x05FFFFFF  
- EEPROM: 0x00FE0000 - 0x00FE1FFF

## Safety Considerations

### Memory Protection
- Always backup ECU data before writing
- Validate address ranges before operations
- Use checksums to verify data integrity
- Implement write protection for critical regions

### Connection Safety
- Use proper isolation and protection circuits
- Monitor communication for errors and timeouts
- Implement graceful disconnect procedures
- Handle ECU reset scenarios

### Error Handling
```python
try:
    bridge = quick_connect(ECUType.BOSCH_ME17, "/dev/ttyUSB0")
    data = bridge.read_memory(0x1000, 256)
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
except MemoryAccessError as e:
    logger.error(f"Memory access failed: {e}")
finally:
    bridge.disconnect()
```

## Troubleshooting

### Connection Issues
1. **Check physical connections** - Ensure K-Line/CAN connections are secure
2. **Verify port permissions** - `sudo chmod 666 /dev/ttyUSB0`
3. **Test with different baud rates** - Try alternative speeds
4. **Check ECU power** - Ensure ECU has proper 12V supply

### CAN Bus Problems
1. **Configure interface** - `sudo ip link set can0 up type can bitrate 500000`
2. **Check termination** - Ensure 120Ω termination resistors
3. **Monitor traffic** - Use `candump can0` to verify messages
4. **Try different bitrates** - Some ECUs use 250kbps or 1Mbps

### Memory Access Errors
1. **Check address ranges** - Ensure addresses are valid for ECU type
2. **Verify session state** - Some operations require specific diagnostic sessions
3. **Monitor for security access** - Some ECUs require seed/key authentication
4. **Check write protection** - Some regions may be protected

## Advanced Features

### Custom Protocol Implementation
```python
from cashout_studio.ecu import ECUProtocol, ECUConfig

class CustomECUProtocol(ECUProtocol):
    def connect(self) -> bool:
        # Implementation specific connection logic
        pass
    
    def read_data(self, address: int, length: int) -> bytes:
        # Custom read implementation
        pass
    
    # ... implement other abstract methods
```

### Memory Analysis Tools
```python
from cashout_studio.utils import analyze_ecu_data, hex_dump

data = bridge.read_memory(0x1000, 1024)
analysis = analyze_ecu_data(data)

print(f"Strings found: {len(analysis['strings'])}")
print(f"Checksums: {analysis['checksums']}")
print(hex_dump(data, 0x1000))
```

### Batch Operations
```python
# Read multiple memory regions
regions = [
    (0x00001000, 256),
    (0x00002000, 512),
    (0x00003000, 1024)
]

for address, length in regions:
    data = bridge.read_memory(address, length)
    with open(f"region_{address:08X}.bin", "wb") as f:
        f.write(data)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement ECU protocol or enhancement
4. Add tests and documentation
5. Submit pull request

### Adding New ECU Support
1. Create protocol class inheriting from `ECUProtocol`
2. Implement all abstract methods
3. Add ECU type to `ECUType` enum
4. Register protocol in bridge layer
5. Add configuration templates
6. Update documentation

## License

CashoutStudio-v1 is released under the MIT License. See LICENSE file for details.

## Support

For support and questions:
- GitHub Issues: https://github.com/eedgurr/CashoutStudio-v1/issues
- Documentation: See `/docs` directory for detailed protocol specifications
- Examples: See `/examples` directory for usage examples

## Disclaimer

This software is intended for educational and research purposes. Users are responsible for ensuring compliance with local laws and regulations. Modifying ECU software may void warranties and could potentially cause vehicle damage or safety issues. Always backup original ECU data before making modifications.