"""
Configuration management for ECU settings and profiles
"""

import json
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger

from ..ecu import ECUType, ECUConfig, ConnectionType


@dataclass
class ECUProfile:
    """ECU profile configuration"""
    name: str
    ecu_type: ECUType
    config: ECUConfig
    description: str = ""
    memory_regions: List[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'ecu_type': self.ecu_type.value,
            'config': {
                'ecu_type': self.config.ecu_type.value,
                'connection_type': self.config.connection_type.value,
                'port': self.config.port,
                'baud_rate': self.config.baud_rate,
                'can_bitrate': self.config.can_bitrate,
                'timeout': self.config.timeout,
                'retries': self.config.retries
            },
            'description': self.description,
            'memory_regions': self.memory_regions or []
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ECUProfile':
        """Create from dictionary (JSON deserialization)"""
        config_data = data['config']
        config = ECUConfig(
            ecu_type=ECUType(config_data['ecu_type']),
            connection_type=ConnectionType(config_data['connection_type']),
            port=config_data['port'],
            baud_rate=config_data['baud_rate'],
            can_bitrate=config_data['can_bitrate'],
            timeout=config_data['timeout'],
            retries=config_data['retries']
        )
        
        return cls(
            name=data['name'],
            ecu_type=ECUType(data['ecu_type']),
            config=config,
            description=data.get('description', ''),
            memory_regions=data.get('memory_regions', [])
        )


class ConfigManager:
    """Manages ECU configuration profiles and settings"""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Default to user's config directory
            home = Path.home()
            self.config_dir = home / '.cashout_studio'
        
        self.config_dir.mkdir(exist_ok=True)
        self.profiles_file = self.config_dir / 'ecu_profiles.json'
        self.settings_file = self.config_dir / 'settings.json'
        
        self.profiles: Dict[str, ECUProfile] = {}
        self.settings: Dict[str, Any] = {}
        
        self._load_profiles()
        self._load_settings()
        self._create_default_profiles()
    
    def _load_profiles(self):
        """Load ECU profiles from file"""
        try:
            if self.profiles_file.exists():
                with open(self.profiles_file, 'r') as f:
                    data = json.load(f)
                
                for name, profile_data in data.items():
                    try:
                        self.profiles[name] = ECUProfile.from_dict(profile_data)
                    except Exception as e:
                        logger.warning(f"Failed to load profile '{name}': {e}")
        except Exception as e:
            logger.error(f"Failed to load profiles: {e}")
    
    def _load_settings(self):
        """Load application settings from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
        
        # Set defaults
        defaults = {
            'default_timeout': 5.0,
            'default_retries': 3,
            'log_level': 'INFO',
            'auto_detect_ports': ['/dev/ttyUSB0', '/dev/ttyUSB1', 'can0'],
            'backup_before_write': True,
            'verify_after_write': True
        }
        
        for key, value in defaults.items():
            if key not in self.settings:
                self.settings[key] = value
    
    def _create_default_profiles(self):
        """Create default ECU profiles if they don't exist"""
        defaults = [
            {
                'name': 'Bosch_ME17_Serial',
                'ecu_type': ECUType.BOSCH_ME17,
                'config': ECUConfig(
                    ecu_type=ECUType.BOSCH_ME17,
                    connection_type=ConnectionType.SERIAL,
                    port='/dev/ttyUSB0',
                    baud_rate=38400,
                    timeout=5.0,
                    retries=3
                ),
                'description': 'Bosch ME17 via Serial/K-Line'
            },
            {
                'name': 'Siemens_MSV_CAN',
                'ecu_type': ECUType.SIEMENS_MSV,
                'config': ECUConfig(
                    ecu_type=ECUType.SIEMENS_MSV,
                    connection_type=ConnectionType.CAN_BUS,
                    port='can0',
                    can_bitrate=500000,
                    timeout=5.0,
                    retries=3
                ),
                'description': 'Siemens MSV via CAN Bus'
            },
            {
                'name': 'Denso_SH705x_Serial',
                'ecu_type': ECUType.DENSO_SH705X,
                'config': ECUConfig(
                    ecu_type=ECUType.DENSO_SH705X,
                    connection_type=ConnectionType.SERIAL,
                    port='/dev/ttyUSB1',
                    baud_rate=19200,
                    timeout=10.0,  # Denso can be slower
                    retries=5
                ),
                'description': 'Denso SH705x via Serial'
            }
        ]
        
        for default in defaults:
            if default['name'] not in self.profiles:
                profile = ECUProfile(**default)
                self.profiles[profile.name] = profile
        
        self.save_profiles()
    
    def save_profiles(self):
        """Save ECU profiles to file"""
        try:
            data = {}
            for name, profile in self.profiles.items():
                data[name] = profile.to_dict()
            
            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")
    
    def save_settings(self):
        """Save application settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def add_profile(self, profile: ECUProfile) -> bool:
        """Add or update an ECU profile"""
        try:
            self.profiles[profile.name] = profile
            self.save_profiles()
            logger.info(f"Added/updated profile: {profile.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add profile: {e}")
            return False
    
    def remove_profile(self, name: str) -> bool:
        """Remove an ECU profile"""
        if name in self.profiles:
            del self.profiles[name]
            self.save_profiles()
            logger.info(f"Removed profile: {name}")
            return True
        return False
    
    def get_profile(self, name: str) -> Optional[ECUProfile]:
        """Get an ECU profile by name"""
        return self.profiles.get(name)
    
    def list_profiles(self, ecu_type: Optional[ECUType] = None) -> List[ECUProfile]:
        """List all profiles, optionally filtered by ECU type"""
        profiles = list(self.profiles.values())
        
        if ecu_type:
            profiles = [p for p in profiles if p.ecu_type == ecu_type]
        
        return sorted(profiles, key=lambda p: p.name)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get application setting"""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Set application setting"""
        self.settings[key] = value
        self.save_settings()
    
    def export_config(self, filename: str) -> bool:
        """Export all configuration to a file"""
        try:
            export_data = {
                'profiles': {name: profile.to_dict() for name, profile in self.profiles.items()},
                'settings': self.settings,
                'version': '1.0',
                'exported_at': time.time()
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Configuration exported to: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return False
    
    def import_config(self, filename: str, merge: bool = True) -> bool:
        """Import configuration from a file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            if not merge:
                self.profiles.clear()
                self.settings.clear()
            
            # Import profiles
            for name, profile_data in data.get('profiles', {}).items():
                try:
                    profile = ECUProfile.from_dict(profile_data)
                    self.profiles[name] = profile
                except Exception as e:
                    logger.warning(f"Failed to import profile '{name}': {e}")
            
            # Import settings
            for key, value in data.get('settings', {}).items():
                self.settings[key] = value
            
            self.save_profiles()
            self.save_settings()
            
            logger.info(f"Configuration imported from: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False


# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager