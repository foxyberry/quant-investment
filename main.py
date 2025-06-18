#!/usr/bin/env python
# coding: utf-8

import backtrader as bt
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import time
from screening.screening_all import BasicInfoScreener
import os


def main():
    
    bis = BasicInfoScreener()
    filename = "basic_info.csv"
    
    bis.get_sp500_symbols()






if __name__ == '__main__':
    main()