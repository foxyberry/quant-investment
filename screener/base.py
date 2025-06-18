import logging
from abc import ABC, abstractmethod
from typing import List, Dict


class SmartStockScreener(ABC):
    """
    Abstract base class for stock screeners.
    All custom screeners should inherit from this class.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)

    @abstractmethod
    def run_screening(self) -> List[Dict]:
        """
        Run the screening process and return a list of filtered stock results.
        Each item in the list should be a dictionary with relevant stock data.
        """
        pass

    def log_info(self, message: str):
        self.logger.info(message)

    def log_warning(self, message: str):
        self.logger.warning(message)

    def log_error(self, message: str):
        self.logger.error(message)
