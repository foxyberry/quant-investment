import os
import pandas as pd
import logging
from typing import List
from datetime import datetime
from .screening_criteria import ScreeningCriteria
from utils.config_manager import ConfigManager
from utils.timezone_utils import get_current_market_time, make_timezone_aware

class BasicInfoScreener:
    """
    기본 정보 기반 스크리너
    - 가격, 거래량, 시가총액 등 기본 필터링
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = ConfigManager()

    def get_snp500_basic_info(self) -> pd.DataFrame:
        """
        S&P 500 종목들의 기본 정보를 가져옵니다.
        
        Returns:
            DataFrame with basic info
        """
        try:
            file_path = self.config.get_basic_info_file_path()
            
            # Check if file exists and is recent (within 1 day)
            if os.path.exists(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                # Make file_time timezone-aware in US Eastern
                file_time = make_timezone_aware(file_time)
                current_time = get_current_market_time()
                
                # If file is less than 1 day old, use cached data
                if (current_time - file_time).days < 1:
                    self.logger.info("Using cached basic info data")
                    return pd.read_csv(file_path)
            
            self.logger.warning("Basic info file not found or outdated. Please run data collection first.")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Failed to load basic info: {e}")
            return pd.DataFrame()

    def apply_basic_filters(self, df: pd.DataFrame, criteria) -> pd.DataFrame:
        """
        기본 필터를 적용합니다.
        
        Args:
            df: 기본 정보 DataFrame
            criteria: 필터링 기준
            
        Returns:
            필터링된 DataFrame
        """
        if df.empty:
            return df
            
        filtered_df = df.copy()
        
        # 가격 필터
        if criteria.min_price:
            filtered_df = filtered_df[filtered_df['price'] >= criteria.min_price]
        if criteria.max_price:
            filtered_df = filtered_df[filtered_df['price'] <= criteria.max_price]
            
        # 거래량 필터
        if criteria.min_volume:
            filtered_df = filtered_df[filtered_df['volume'] >= criteria.min_volume]
            
        # 시가총액 필터
        if criteria.min_market_cap:
            filtered_df = filtered_df[filtered_df['market_cap'] >= criteria.min_market_cap]
            
        # 섹터 필터
        if criteria.sectors:
            filtered_df = filtered_df[filtered_df['sector'].isin(criteria.sectors)]
            
        return filtered_df
