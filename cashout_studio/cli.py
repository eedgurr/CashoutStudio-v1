"""
Command-line interface for CashoutStudio ECU operations
"""

import argparse
import sys
import time
from typing import Optional

from loguru import logger

from cashout_studio.ecu import ECUType, ECUConfig, ConnectionType  
from cashout_studio.bridge import ECUBridge, quick_connect, auto_detect_ecu


def setup_logging(verbose: bool = False):
    """Configure logging"""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, format="{time} | {level} | {message}")


def cmd_list_ecus(args):
    """List supported ECU types"""
    print("Supported ECU Types:")
    for ecu_type in ECUType:
        print(f"  - {ecu_type.value}")


def cmd_connect(args):
    """Connect to an ECU"""
    try:
        ecu_type = ECUType(args.ecu_type)
        bridge = quick_connect(ecu_type, args.port)
        
        print(f"Successfully connected to {ecu_type.value}")
        
        # Get and display ECU info
        info = bridge.get_ecu_info()
        print("\nECU Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # Get diagnostic codes if requested
        if args.read_dtc:
            dtc_codes = bridge.get_diagnostic_codes()
            print(f"\nDiagnostic Codes: {len(dtc_codes)} found")
            for code in dtc_codes:
                print(f"  - {code}")
        
        bridge.disconnect()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def cmd_auto_detect(args):
    """Auto-detect ECU type"""
    ports = args.ports if args.ports else ["/dev/ttyUSB0", "/dev/ttyUSB1", "can0"]
    
    print(f"Scanning ports: {', '.join(ports)}")
    detected_ecu = auto_detect_ecu(ports)
    
    if detected_ecu:
        print(f"Detected ECU: {detected_ecu.value}")
    else:
        print("No ECU detected")
        sys.exit(1)


def cmd_read_memory(args):
    """Read memory from ECU"""
    try:
        ecu_type = ECUType(args.ecu_type)
        bridge = quick_connect(ecu_type, args.port)
        
        address = int(args.address, 16) if args.address.startswith('0x') else int(args.address)
        length = args.length
        
        print(f"Reading {length} bytes from address 0x{address:08X}")
        
        data = bridge.read_memory(address, length)
        
        # Display data as hex dump
        print(f"\nData ({len(data)} bytes):")
        for i in range(0, len(data), 16):
            hex_data = ' '.join(f'{b:02X}' for b in data[i:i+16])
            ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])
            print(f"{address+i:08X}: {hex_data:<48} {ascii_data}")
        
        if args.output:
            with open(args.output, 'wb') as f:
                f.write(data)
            print(f"\nData written to: {args.output}")
        
        bridge.disconnect()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def cmd_write_memory(args):
    """Write memory to ECU"""
    try:
        ecu_type = ECUType(args.ecu_type)
        bridge = quick_connect(ecu_type, args.port)
        
        address = int(args.address, 16) if args.address.startswith('0x') else int(args.address)
        
        # Read data from file or parse hex string
        if args.file:
            with open(args.file, 'rb') as f:
                data = f.read()
        elif args.data:
            # Parse hex string
            hex_str = args.data.replace('0x', '').replace(' ', '')
            data = bytes.fromhex(hex_str)
        else:
            print("Error: Must specify either --file or --data")
            sys.exit(1)
        
        print(f"Writing {len(data)} bytes to address 0x{address:08X}")
        
        if not args.force:
            response = input("This will modify ECU memory. Continue? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled")
                sys.exit(0)
        
        success = bridge.write_memory(address, data)
        
        if success:
            print("Write completed successfully")
        else:
            print("Write failed")
            sys.exit(1)
        
        bridge.disconnect()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def cmd_clear_dtc(args):
    """Clear diagnostic trouble codes"""
    try:
        ecu_type = ECUType(args.ecu_type)
        bridge = quick_connect(ecu_type, args.port)
        
        print("Clearing diagnostic trouble codes...")
        success = bridge.clear_diagnostic_codes()
        
        if success:
            print("DTCs cleared successfully")
        else:
            print("Failed to clear DTCs")
            sys.exit(1)
        
        bridge.disconnect()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="CashoutStudio ECU Management Tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List ECUs command
    list_parser = subparsers.add_parser("list", help="List supported ECU types")
    list_parser.set_defaults(func=cmd_list_ecus)
    
    # Connect command
    connect_parser = subparsers.add_parser("connect", help="Connect to an ECU")
    connect_parser.add_argument("ecu_type", help="ECU type (bosch_me17, siemens_msv, denso_sh705x)")
    connect_parser.add_argument("port", help="Connection port (/dev/ttyUSB0, can0, etc)")
    connect_parser.add_argument("--read-dtc", action="store_true", help="Read diagnostic codes")
    connect_parser.set_defaults(func=cmd_connect)
    
    # Auto-detect command
    detect_parser = subparsers.add_parser("detect", help="Auto-detect ECU type")
    detect_parser.add_argument("--ports", nargs="+", help="Ports to scan")
    detect_parser.set_defaults(func=cmd_auto_detect)
    
    # Read memory command
    read_parser = subparsers.add_parser("read", help="Read ECU memory")
    read_parser.add_argument("ecu_type", help="ECU type")
    read_parser.add_argument("port", help="Connection port")
    read_parser.add_argument("address", help="Memory address (hex or decimal)")
    read_parser.add_argument("length", type=int, help="Number of bytes to read")
    read_parser.add_argument("-o", "--output", help="Output file for data")
    read_parser.set_defaults(func=cmd_read_memory)
    
    # Write memory command  
    write_parser = subparsers.add_parser("write", help="Write ECU memory")
    write_parser.add_argument("ecu_type", help="ECU type")
    write_parser.add_argument("port", help="Connection port")
    write_parser.add_argument("address", help="Memory address (hex or decimal)")
    write_parser.add_argument("--file", help="File containing data to write")
    write_parser.add_argument("--data", help="Hex data string to write")
    write_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    write_parser.set_defaults(func=cmd_write_memory)
    
    # Clear DTC command
    clear_parser = subparsers.add_parser("clear-dtc", help="Clear diagnostic codes")
    clear_parser.add_argument("ecu_type", help="ECU type")
    clear_parser.add_argument("port", help="Connection port")
    clear_parser.set_defaults(func=cmd_clear_dtc)
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()