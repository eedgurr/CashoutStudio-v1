"""
Example usage of CashoutStudio ECU Bridge
"""

import sys
import time
from loguru import logger

from cashout_studio.ecu import ECUType, ECUConfig, ConnectionType
from cashout_studio.bridge import ECUBridge, quick_connect, auto_detect_ecu
from cashout_studio.utils import hex_dump, analyze_ecu_data
from cashout_studio.config import get_config_manager

def example_basic_connection():
    """Example: Basic ECU connection and info retrieval"""
    print("=== Basic ECU Connection Example ===")
    
    try:
        # Quick connect to a Bosch ME17 ECU
        bridge = quick_connect(ECUType.BOSCH_ME17, "/dev/ttyUSB0")
        
        # Get ECU information
        info = bridge.get_ecu_info()
        print("ECU Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # Read diagnostic codes
        dtc_codes = bridge.get_diagnostic_codes()
        print(f"\nDiagnostic Codes: {len(dtc_codes)} found")
        for code in dtc_codes:
            print(f"  - {code}")
        
        # Disconnect
        bridge.disconnect()
        print("\nDisconnected successfully")
        
    except Exception as e:
        print(f"Error: {str(e)}")


def example_memory_operations():
    """Example: Memory read/write operations"""
    print("=== Memory Operations Example ===")
    
    try:
        bridge = quick_connect(ECUType.DENSO_SH705X, "/dev/ttyUSB1")
        
        # Read some memory
        address = 0x00001000
        length = 256
        
        print(f"Reading {length} bytes from address 0x{address:08X}")
        data = bridge.read_memory(address, length)
        
        # Display as hex dump
        print("\nMemory content:")
        print(hex_dump(data, address))
        
        # Analyze the data
        analysis = analyze_ecu_data(data)
        print(f"\nData Analysis:")
        print(f"  Size: {analysis['size_formatted']}")
        print(f"  Checksums: {analysis['checksums']}")
        print(f"  Strings found: {len(analysis['strings'])}")
        
        for string_info in analysis['strings'][:5]:  # Show first 5 strings
            print(f"    @0x{string_info['offset']:04X}: '{string_info['text']}'")
        
        # Example write (commented out for safety)
        # bridge.write_memory(0x50000000, b'\x01\x02\x03\x04')
        
        bridge.disconnect()
        
    except Exception as e:
        print(f"Error: {str(e)}")


def example_multi_ecu_session():
    """Example: Working with multiple ECU types"""
    print("=== Multi-ECU Session Example ===")
    
    bridge = ECUBridge()
    
    ecu_configs = [
        (ECUType.BOSCH_ME17, "/dev/ttyUSB0"),
        (ECUType.SIEMENS_MSV, "can0"),
        (ECUType.DENSO_SH705X, "/dev/ttyUSB1")
    ]
    
    for ecu_type, port in ecu_configs:
        try:
            print(f"\nConnecting to {ecu_type.value}...")
            
            if ecu_type == ECUType.BOSCH_ME17:
                config = ECUConfig(ecu_type, ConnectionType.SERIAL, port, baud_rate=38400)
            elif ecu_type == ECUType.SIEMENS_MSV:
                config = ECUConfig(ecu_type, ConnectionType.CAN_BUS, port, can_bitrate=500000)
            else:  # DENSO_SH705X
                config = ECUConfig(ecu_type, ConnectionType.SERIAL, port, baud_rate=19200)
            
            bridge.configure_ecu(ecu_type, config)
            
            if bridge.connect(ecu_type):
                info = bridge.get_ecu_info(ecu_type)
                print(f"  Connected! ECU: {info.get('ecu_type', 'Unknown')}")
                
                # Get session info
                session = bridge.get_active_session()
                if session:
                    print(f"  Session created at: {time.ctime(session.connected_at)}")
                
                bridge.disconnect(ecu_type)
            else:
                print(f"  Failed to connect")
                
        except Exception as e:
            print(f"  Error with {ecu_type.value}: {str(e)}")
    
    print("\nMulti-ECU test completed")


def example_config_management():
    """Example: Configuration management"""
    print("=== Configuration Management Example ===")
    
    config_manager = get_config_manager()
    
    # List available profiles
    profiles = config_manager.list_profiles()
    print(f"Available profiles: {len(profiles)}")
    for profile in profiles:
        print(f"  - {profile.name}: {profile.ecu_type.value} ({profile.description})")
    
    # Get a specific profile
    bosch_profile = config_manager.get_profile('Bosch_ME17_Serial')
    if bosch_profile:
        print(f"\nBosch ME17 Profile:")
        print(f"  Port: {bosch_profile.config.port}")
        print(f"  Baud Rate: {bosch_profile.config.baud_rate}")
        print(f"  Timeout: {bosch_profile.config.timeout}")
    
    # Create a custom profile
    from cashout_studio.ecu import ECUConfig
    from cashout_studio.config import ECUProfile
    
    custom_config = ECUConfig(
        ecu_type=ECUType.BOSCH_ME17,
        connection_type=ConnectionType.SERIAL,
        port="/dev/ttyUSB2",
        baud_rate=57600,
        timeout=10.0
    )
    
    custom_profile = ECUProfile(
        name="Bosch_ME17_Custom",
        ecu_type=ECUType.BOSCH_ME17,
        config=custom_config,
        description="Custom Bosch ME17 configuration"
    )
    
    if config_manager.add_profile(custom_profile):
        print(f"\nAdded custom profile: {custom_profile.name}")
    
    # Show settings
    print(f"\nCurrent settings:")
    print(f"  Default timeout: {config_manager.get_setting('default_timeout')}")
    print(f"  Auto-detect ports: {config_manager.get_setting('auto_detect_ports')}")
    print(f"  Backup before write: {config_manager.get_setting('backup_before_write')}")


def example_auto_detection():
    """Example: Auto-detection of ECU type"""
    print("=== Auto-Detection Example ===")
    
    # Define ports to scan
    ports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyS0", "can0"]
    
    print(f"Scanning ports: {', '.join(ports)}")
    
    detected_ecu = auto_detect_ecu(ports)
    
    if detected_ecu:
        print(f"Detected ECU: {detected_ecu.value}")
        
        # Try to connect with the detected type
        try:
            bridge = ECUBridge()
            # Note: auto_detect_ecu would need to return port info too in a real implementation
            print("Would connect to detected ECU here...")
        except Exception as e:
            print(f"Error connecting to detected ECU: {e}")
    else:
        print("No ECU detected on any port")


def example_error_handling():
    """Example: Proper error handling"""
    print("=== Error Handling Example ===")
    
    bridge = ECUBridge()
    
    try:
        # Try to connect to non-existent port
        config = ECUConfig(
            ecu_type=ECUType.BOSCH_ME17,
            connection_type=ConnectionType.SERIAL,
            port="/dev/nonexistent",
            baud_rate=38400,
            timeout=2.0,  # Short timeout
            retries=1
        )
        
        bridge.configure_ecu(ECUType.BOSCH_ME17, config)
        
        if not bridge.connect(ECUType.BOSCH_ME17):
            print("Connection failed as expected")
        
        # Try to read memory without connection
        try:
            data = bridge.read_memory(0x1000, 16)
        except Exception as e:
            print(f"Memory read failed as expected: {str(e)}")
        
        print("Error handling test completed")
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


def main():
    """Run all examples"""
    
    # Configure logging for examples
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")
    
    examples = [
        example_basic_connection,
        example_memory_operations,
        example_multi_ecu_session,
        example_config_management,
        example_auto_detection,
        example_error_handling
    ]
    
    print("CashoutStudio ECU Bridge Examples")
    print("=" * 50)
    print("\nNote: These examples require actual ECU hardware connections.")
    print("Modify port names and configurations to match your setup.\n")
    
    for i, example_func in enumerate(examples, 1):
        print(f"\n{i}. Running {example_func.__name__}")
        print("-" * 40)
        
        try:
            example_func()
        except KeyboardInterrupt:
            print("\nExample interrupted by user")
            break
        except Exception as e:
            print(f"Example failed with error: {str(e)}")
        
        if i < len(examples):
            input("\nPress Enter to continue to next example...")
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    main()