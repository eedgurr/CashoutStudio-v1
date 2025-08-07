#!/usr/bin/env python3
"""
Basic test script for CashoutStudio ECU framework
This script validates that all ECU protocols can be instantiated and configured properly.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_ecu_framework():
    """Test the ECU framework components"""
    print("Testing CashoutStudio ECU Framework")
    print("=" * 50)
    
    # Test 1: Import core components
    try:
        from cashout_studio.ecu import ECUType, ECUConfig, ConnectionType, ECUManager
        print("✓ Core ECU components imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import core ECU components: {e}")
        return False
    
    # Test 2: Test ECU types enumeration
    try:
        ecu_types = list(ECUType)
        expected_types = ['bosch_me17', 'siemens_msv', 'denso_sh705x']
        assert len(ecu_types) == 3
        assert all(ecu.value in expected_types for ecu in ecu_types)
        print(f"✓ ECU types available: {[ecu.value for ecu in ecu_types]}")
    except Exception as e:
        print(f"✗ ECU types test failed: {e}")
        return False
    
    # Test 3: Import all protocol implementations
    try:
        from cashout_studio.protocols import BoschME17Protocol, SiemensMSVProtocol, DensoSH705xProtocol
        print("✓ All protocol implementations imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import protocols: {e}")
        return False
    
    # Test 4: Test ECU configuration creation
    try:
        configs = [
            ECUConfig(ECUType.BOSCH_ME17, ConnectionType.SERIAL, "/dev/ttyUSB0", baud_rate=38400),
            ECUConfig(ECUType.SIEMENS_MSV, ConnectionType.CAN_BUS, "can0", can_bitrate=500000),
            ECUConfig(ECUType.DENSO_SH705X, ConnectionType.SERIAL, "/dev/ttyUSB1", baud_rate=19200)
        ]
        print(f"✓ Created {len(configs)} ECU configurations")
    except Exception as e:
        print(f"✗ ECU configuration creation failed: {e}")
        return False
    
    # Test 5: Test protocol instantiation
    try:
        protocols = []
        for config in configs:
            if config.ecu_type == ECUType.BOSCH_ME17:
                protocol = BoschME17Protocol(config)
            elif config.ecu_type == ECUType.SIEMENS_MSV:
                protocol = SiemensMSVProtocol(config)
            elif config.ecu_type == ECUType.DENSO_SH705X:
                protocol = DensoSH705xProtocol(config)
            
            protocols.append(protocol)
            assert protocol.config == config
            assert not protocol.connected  # Should start disconnected
        
        print(f"✓ Instantiated {len(protocols)} protocol handlers")
    except Exception as e:
        print(f"✗ Protocol instantiation failed: {e}")
        return False
    
    # Test 6: Test ECU Manager
    try:
        manager = ECUManager()
        
        # Register all protocols
        for i, protocol in enumerate(protocols):
            ecu_type = list(ECUType)[i]
            manager.register_protocol(ecu_type, protocol)
        
        supported_ecus = manager.list_supported_ecus()
        assert len(supported_ecus) == 3
        print(f"✓ ECU Manager registered {len(supported_ecus)} protocols")
    except Exception as e:
        print(f"✗ ECU Manager test failed: {e}")
        return False
    
    # Test 7: Test Bridge Layer
    try:
        from cashout_studio.bridge import ECUBridge
        bridge = ECUBridge()
        
        supported_ecus = bridge.get_supported_ecus()
        assert len(supported_ecus) >= 3
        print(f"✓ ECU Bridge initialized with {len(supported_ecus)} supported ECUs")
    except Exception as e:
        print(f"✗ ECU Bridge test failed: {e}")
        return False
    
    # Test 8: Test Configuration System
    try:
        from cashout_studio.config import get_config_manager
        config_manager = get_config_manager()
        
        profiles = config_manager.list_profiles()
        assert len(profiles) >= 3  # Should have default profiles
        print(f"✓ Configuration system loaded {len(profiles)} profiles")
    except Exception as e:
        print(f"✗ Configuration system test failed: {e}")
        return False
    
    # Test 9: Test Utility Functions
    try:
        from cashout_studio.utils import hex_dump, analyze_ecu_data, calculate_checksum
        
        test_data = b'\x01\x02\x03\x04Hello World!\x00\xFF'
        
        # Test hex dump
        dump = hex_dump(test_data, 0x1000)
        assert 'Hello World!' in dump
        
        # Test data analysis
        analysis = analyze_ecu_data(test_data)
        assert 'strings' in analysis
        assert len(analysis['strings']) > 0
        
        # Test checksum calculation
        checksum = calculate_checksum(test_data, 'sum')
        assert isinstance(checksum, int)
        
        print("✓ Utility functions working correctly")
    except Exception as e:
        print(f"✗ Utility functions test failed: {e}")
        return False
    
    # Test 10: Test CLI Module Import
    try:
        from cashout_studio import cli
        print("✓ CLI module imported successfully")
    except ImportError as e:
        print(f"✗ CLI module import failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✓ All tests passed! ECU framework is working correctly.")
    print("\nNext steps:")
    print("1. Connect ECU hardware to test actual communication")
    print("2. Use 'PYTHONPATH=. python cashout_studio/cli.py list' to see supported ECUs")
    print("3. Run examples in examples/ecu_examples.py for detailed usage")
    print("4. Check ECU_SUPPORT.md for comprehensive documentation")
    
    return True

def test_mock_connection():
    """Test mock connection (without hardware)"""
    print("\n" + "-" * 30)
    print("Testing Mock Connection")
    print("-" * 30)
    
    try:
        from cashout_studio.ecu import ECUType, ECUConfig, ConnectionType
        from cashout_studio.protocols.bosch_me17 import BoschME17Protocol
        
        # Create a mock configuration
        config = ECUConfig(
            ecu_type=ECUType.BOSCH_ME17,
            connection_type=ConnectionType.SERIAL,
            port="/dev/null",  # Use /dev/null as a safe mock port
            baud_rate=38400,
            timeout=1.0
        )
        
        protocol = BoschME17Protocol(config)
        
        # Test that protocol object is created properly
        assert protocol.config.ecu_type == ECUType.BOSCH_ME17
        assert protocol.config.port == "/dev/null"
        assert not protocol.connected
        
        print("✓ Mock protocol configuration successful")
        
        # Note: We don't actually try to connect since there's no hardware
        print("✓ Mock connection test completed (no hardware required)")
        
    except Exception as e:
        print(f"✗ Mock connection test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("CashoutStudio ECU Framework Test Suite")
    print("Date: " + str(__import__('datetime').datetime.now()))
    print()
    
    success = True
    success &= test_ecu_framework()
    success &= test_mock_connection()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)