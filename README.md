# CashoutStudio-v1

**Offline AI tuning canvas + Web3 signatures with comprehensive ECU support**

CashoutStudio-v1 is a professional-grade automotive ECU (Engine Control Unit) communication framework designed for tuning applications. It provides a unified Python interface for communicating with multiple ECU brands and protocols, enabling seamless data exchange for calibration, diagnostics, and firmware modification.

## 🚀 Features

### Supported ECU Types
- **Bosch ME17** - KWP2000 over K-Line/Serial
- **Siemens MSV** - UDS/ISO 14229 over CAN Bus or Serial  
- **Denso SH705x** - Proprietary protocol over Serial

### Core Capabilities
- **Memory Operations** - Read/write ECU memory with address validation
- **Diagnostic Codes** - Read and clear DTCs (Diagnostic Trouble Codes)
- **ECU Identification** - Retrieve part numbers, software versions, hardware info
- **Multi-Protocol Support** - Unified interface for different ECU communication protocols
- **Session Management** - Connection tracking and graceful disconnect handling
- **Configuration Profiles** - Persistent storage of ECU settings and connection parameters

### Communication Interfaces
- Serial/RS232 (K-Line, proprietary protocols)
- CAN Bus (ISO 11898, UDS messaging)
- USB (via USB-to-Serial adapters)
- Future: Ethernet support

## 📦 Installation

### Prerequisites
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-dev python3-pip can-utils

# Enable CAN interface (if using CAN Bus)
sudo modprobe can
sudo modprobe can_raw
sudo ip link set can0 up type can bitrate 500000
```

### Install CashoutStudio
```bash
git clone https://github.com/eedgurr/CashoutStudio-v1.git
cd CashoutStudio-v1
pip install -r requirements.txt
```

## 🔧 Quick Start

### Command Line Interface
```bash
# List supported ECU types
PYTHONPATH=. python cashout_studio/cli.py list

# Connect to Bosch ME17 ECU
PYTHONPATH=. python cashout_studio/cli.py connect bosch_me17 /dev/ttyUSB0 --read-dtc

# Auto-detect ECU type
PYTHONPATH=. python cashout_studio/cli.py detect --ports /dev/ttyUSB0 /dev/ttyUSB1

# Read ECU memory
PYTHONPATH=. python cashout_studio/cli.py read bosch_me17 /dev/ttyUSB0 0x1000 256 -o memory_dump.bin

# Clear diagnostic codes
PYTHONPATH=. python cashout_studio/cli.py clear-dtc siemens_msv can0
```

### Python API
```python
from cashout_studio.bridge import quick_connect
from cashout_studio.ecu import ECUType

# Quick connection to ECU
bridge = quick_connect(ECUType.BOSCH_ME17, "/dev/ttyUSB0")

# Get ECU information
info = bridge.get_ecu_info()
print(f"Connected to: {info['ecu_type']}")
print(f"Part Number: {info.get('part_number', 'Unknown')}")

# Read memory
data = bridge.read_memory(0x00001000, 256)
print(f"Read {len(data)} bytes from ECU")

# Read diagnostic codes
dtc_codes = bridge.get_diagnostic_codes()
print(f"DTC Codes: {dtc_codes}")

# Clean disconnect
bridge.disconnect()
```

### Advanced Usage
```python
from cashout_studio.bridge import ECUBridge
from cashout_studio.ecu import ECUType, ECUConfig, ConnectionType

# Create bridge with custom configuration
bridge = ECUBridge()

config = ECUConfig(
    ecu_type=ECUType.SIEMENS_MSV,
    connection_type=ConnectionType.CAN_BUS,
    port="can0",
    can_bitrate=500000,
    timeout=10.0
)

bridge.configure_ecu(ECUType.SIEMENS_MSV, config)
bridge.connect(ECUType.SIEMENS_MSV)

# Multi-ECU session management
sessions = bridge.list_sessions()
for ecu_type, session in sessions.items():
    print(f"{ecu_type.value}: Connected at {session.connected_at}")
```

## 🏗️ Architecture

```
CashoutStudio-v1/
├── cashout_studio/
│   ├── ecu/              # Core ECU management
│   │   └── __init__.py   # ECUManager, ECUProtocol base classes
│   ├── protocols/        # ECU-specific protocol implementations
│   │   ├── bosch_me17.py
│   │   ├── siemens_msv.py
│   │   └── denso_sh705x.py
│   ├── bridge/           # Unified communication interface
│   │   └── __init__.py   # ECUBridge, session management
│   ├── utils/            # Utility functions and tools
│   ├── config.py         # Configuration management
│   └── cli.py           # Command-line interface
├── examples/            # Usage examples and tutorials
├── ECU_SUPPORT.md      # Detailed ECU documentation
└── test_ecu_framework.py # Test suite
```

## 🔬 Testing

Run the included test suite to verify your installation:

```bash
cd CashoutStudio-v1
python test_ecu_framework.py
```

The test suite validates:
- All ECU protocol implementations
- Configuration system functionality
- Bridge layer operations
- Utility functions
- CLI module imports

## 📋 Protocol Details

### Bosch ME17 (KWP2000)
- **Connection**: Serial/K-Line at 38400 baud
- **Addressing**: 24-bit memory addressing
- **Features**: Flash/RAM access, DTC support, ECU identification
- **Frame Format**: `[Length] [Data] [Checksum]`

### Siemens MSV (UDS/ISO 14229)  
- **Connection**: CAN Bus (500kbps) or Serial
- **Addressing**: Data identifier based access
- **Features**: Multi-frame messaging, diagnostic sessions
- **CAN IDs**: Request 0x7E0, Response 0x7E8

### Denso SH705x (Proprietary)
- **Connection**: Serial with even parity at 19200 baud
- **Addressing**: 32-bit memory addressing  
- **Features**: ROM/RAM/EEPROM access, sector erase, checksum verification
- **Frame Format**: `[STX] [LEN] [CMD] [DATA] [CHK] [ETX]`

## ⚠️ Safety & Legal

- **Always backup ECU data** before making modifications
- **Use proper isolation circuits** when connecting to vehicle systems
- **Verify address ranges** before writing to ECU memory
- **Comply with local laws** regarding vehicle modifications
- **This software is for educational/research purposes**

## 🛠️ Hardware Requirements

### Serial/K-Line Connection
- USB-to-Serial adapter (FTDI recommended)
- K-Line interface circuit (ISO 9141/14230 compatible)
- Proper voltage level translation (12V ↔ 5V/3.3V)

### CAN Bus Connection
- CAN transceiver (MCP2515, SN65HVD230, etc.)
- OBD-II connector or direct ECU access
- 120Ω termination resistors
- Linux SocketCAN support

## 📚 Documentation

- **[ECU_SUPPORT.md](ECU_SUPPORT.md)** - Comprehensive ECU protocol documentation
- **[examples/](examples/)** - Code examples and tutorials
- **Protocol specifications** - Detailed implementation notes in source code

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-ecu-support`)
3. Implement your changes with tests
4. Update documentation
5. Submit a pull request

### Adding New ECU Support
1. Create protocol class inheriting from `ECUProtocol`
2. Implement all abstract methods
3. Add ECU type to `ECUType` enum
4. Register protocol in bridge layer
5. Add configuration templates and documentation

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🆘 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/eedgurr/CashoutStudio-v1/issues)
- **Documentation**: See `/docs` for detailed guides
- **Examples**: Check `/examples` for usage patterns

## 🔗 Related Projects

- **OpenECU** - Open-source ECU simulation
- **J2534** - Standard automotive diagnostic interface
- **OBD-II Tools** - On-board diagnostics utilities

---

**Disclaimer**: This software is intended for educational and research purposes. Users are responsible for ensuring compliance with local laws and regulations. Vehicle modifications may void warranties and could potentially cause safety issues.
