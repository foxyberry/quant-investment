import os
import yaml
from typing import Dict, Any
from pathlib import Path

class ConfigManager:
    """Configuration manager for the quant investment project."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()
    
    def get_history_file_path(self, symbol: str) -> str:
        """Get the history file path for a given symbol."""
        return os.path.join(self.get_history_dir(), f"{symbol}_history.csv")
        
    
    def _load_configs(self) -> None:
        """Load all YAML configuration files from the config directory."""
        config_path = Path(self.config_dir)
        if not config_path.exists():
            raise FileNotFoundError(f"Config directory not found: {self.config_dir}")
        
        for config_file in config_path.glob("*.yaml"):
            with open(config_file, 'r') as f:
                config_name = config_file.stem
                self.configs[config_name] = yaml.safe_load(f)
    
    def get_config(self, config_name: str) -> Dict[str, Any]:
        """Get a specific configuration by name."""
        if config_name not in self.configs:
            raise KeyError(f"Configuration not found: {config_name}")
        return self.configs[config_name]
    
    def get_value(self, config_name: str, *keys: str) -> Any:
        """Get a specific value from a configuration using dot notation."""
        config = self.get_config(config_name)
        value = config
        for key in keys:
            if not isinstance(value, dict):
                raise KeyError(f"Invalid path in configuration: {'.'.join(keys)}")
            value = value.get(key)
            if value is None:
                raise KeyError(f"Key not found in configuration: {key}")
        return value
    
    def get_history_dir(self) -> str:
        """Get the data directory path."""
        return self.get_value("base_config", "data", "history_dir")
    
    def get_snp500_info_file(self) -> str:
        """Get the snp500 info file path."""
        return self.get_value("base_config", "data", "snp500_info_file")
    
    def get_basic_info_file(self) -> str:
        """Get the basic info file path."""
        return self.get_value("base_config", "data", "basic_info_file")
    
    def get_screening_criteria(self) -> Dict[str, Any]:
        """Get the screening criteria configuration."""
        return self.get_config("screening_criteria")
    
    def get_basic_filters(self) -> Dict[str, Any]:
        """Get the basic filters configuration."""
        return self.get_value("screening_criteria", "basic_filters")
    
    def get_technical_analysis_params(self) -> Dict[str, Any]:
        """Get the technical analysis parameters."""
        return self.get_value("screening_criteria", "technical_analysis")
    
    def get_external_filters(self) -> Dict[str, Any]:
        """Get the external filters configuration."""
        return self.get_value("screening_criteria", "external_filters") 