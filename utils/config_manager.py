import os
import yaml
from pathlib import Path
from typing import Dict, Any
import logging

class ConfigManager:
    """Configuration management class for the quant investment system"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration manager
        
        Args:
            config_path: Optional path to config file, defaults to base_config.yaml
        """
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(__file__).parent.parent
        
        if config_path is None:
            config_path = self.project_root / "config" / "base_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in config file: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}
    
    def get_data_dir(self) -> Path:
        """Get data directory path"""
        return self.project_root / self.config.get('data', {}).get('base_dir', 'data')
    
    def get_history_dir(self) -> Path:
        """Get historical data directory path"""
        return self.get_data_dir() / self.config.get('data', {}).get('history_dir', 'history')
    
    def get_logs_dir(self) -> Path:
        """Get logs directory path"""
        return self.project_root / self.config.get('logging', {}).get('log_dir', 'logs')
    
    def get_history_file_path(self, symbol: str) -> str:
        """
        Get file path for individual stock history data
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Full path to the history CSV file
        """
        history_dir = self.get_history_dir()
        return str(history_dir / f"{symbol}_history.csv")
    
    def get_basic_info_file_path(self) -> str:
        """Get path to basic stock information file"""
        return str(self.get_data_dir() / "basic_info.csv")
    
    def get_snp500_info_file_path(self) -> str:
        """Get path to S&P 500 information file"""
        return str(self.get_data_dir() / "snp500_info.csv")
    
    def get_screening_criteria_config(self) -> Dict[str, Any]:
        """Load screening criteria configuration"""
        criteria_path = self.project_root / "config" / "screening_criteria.yaml"
        try:
            with open(criteria_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.logger.debug(f"Screening criteria loaded from {criteria_path}")
                return config
        except FileNotFoundError:
            self.logger.error(f"Screening criteria file not found: {criteria_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in screening criteria: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load screening criteria: {e}")
            return {}
    
    def get_config_value(self, key_path: str, default=None):
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path to config value (e.g., 'data.base_dir')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            self.logger.debug(f"Config key '{key_path}' not found, using default: {default}")
            return default

    def get_screening_criteria(self) -> Dict[str, Any]:
        """Get the screening criteria configuration"""
        return self.get_screening_criteria_config()
    
    def get_basic_filters(self) -> Dict[str, Any]:
        """Get the basic filters configuration"""
        return self.get_screening_criteria_config().get("basic_filters", {})

    def get_technical_analysis_params(self) -> Dict[str, Any]:
        """Get the technical analysis parameters"""
        return self.get_screening_criteria_config().get("technical_analysis", {})
    
    def get_external_filters(self) -> Dict[str, Any]:
        """Get the external filters configuration"""
        return self.get_screening_criteria_config().get("external_filters", {}) 