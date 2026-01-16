#!/usr/bin/env python3
"""
Simple orchestrator for running different trading strategies

Usage:
    python run.py <strategy_file>
    python run.py scripts/screening/tech_breakout.py
    python run.py scripts/backtesting/momentum.py
    python run.py --list
    python run.py --new <type> <name>

This allows users to write their own strategy files with custom criteria
defined directly in Python code, avoiding complex parameter passing.
"""

import sys
import os
import argparse
import importlib.util
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyRunner:
    """Main orchestrator for running user-defined strategies"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.strategies_dir = self.project_root / "scripts"
        self.templates_dir = self.project_root / "docs" / "examples"
        
    def run_strategy(self, strategy_path: str, output_format: str = None):
        """
        Run a user-defined strategy file
        
        Args:
            strategy_path: Path to the strategy Python file
            output_format: Optional output format (csv, json, etc.)
        """
        try:
            # Convert to Path object
            strategy_file = Path(strategy_path)
            
            # Check if file exists
            if not strategy_file.exists():
                # Try relative to my_strategies directory
                strategy_file = self.strategies_dir / strategy_path
                if not strategy_file.exists():
                    logger.error(f"Strategy file not found: {strategy_path}")
                    return False
            
            logger.info(f"Loading strategy: {strategy_file}")
            
            # Load the strategy module dynamically
            spec = importlib.util.spec_from_file_location("user_strategy", strategy_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load strategy module: {strategy_file}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            sys.modules["user_strategy"] = module
            spec.loader.exec_module(module)
            
            # Check if the module has a run() function
            if not hasattr(module, 'run'):
                logger.error(f"Strategy file must have a 'run()' function: {strategy_file}")
                return False
            
            # Execute the strategy
            logger.info("=" * 80)
            logger.info(f"Executing strategy: {strategy_file.stem}")
            logger.info("=" * 80)
            
            start_time = datetime.now()
            results = module.run()
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            logger.info(f"Strategy completed in {execution_time:.2f} seconds")
            
            # Handle output
            if output_format and results is not None:
                self._save_results(results, strategy_file.stem, output_format)
            
            return True
            
        except Exception as e:
            logger.error(f"Error running strategy: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _save_results(self, results, strategy_name: str, output_format: str):
        """Save strategy results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project_root / "results"
        output_dir.mkdir(exist_ok=True)
        
        if output_format == 'csv':
            if isinstance(results, pd.DataFrame):
                output_file = output_dir / f"{strategy_name}_{timestamp}.csv"
                results.to_csv(output_file, index=False)
                logger.info(f"Results saved to: {output_file}")
            elif isinstance(results, list) and results:
                df = pd.DataFrame(results)
                output_file = output_dir / f"{strategy_name}_{timestamp}.csv"
                df.to_csv(output_file, index=False)
                logger.info(f"Results saved to: {output_file}")
            else:
                logger.warning("Results format not suitable for CSV export")
                
        elif output_format == 'json':
            import json
            output_file = output_dir / f"{strategy_name}_{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to: {output_file}")
    
    def list_strategies(self):
        """List all available strategies"""
        logger.info("Available Strategies:")
        logger.info("=" * 50)
        
        if not self.strategies_dir.exists():
            logger.warning(f"Strategies directory not found: {self.strategies_dir}")
            logger.info("Create your strategies in 'scripts/' directory")
            return
        
        # Find all Python files in my_strategies
        for py_file in self.strategies_dir.rglob("*.py"):
            if py_file.name != "__init__.py":
                relative_path = py_file.relative_to(self.strategies_dir)
                logger.info(f"  - {relative_path}")
        
        logger.info("\nUsage: python run.py <strategy_file>")
        logger.info("Example: python run.py scripts/screening/tech_breakout.py")
    
    def create_from_template(self, template_type: str, name: str):
        """Create a new strategy from template"""
        # Map template types to directories
        type_mapping = {
            'screening': 'screening',
            'screen': 'screening',
            'backtest': 'backtesting',
            'backtesting': 'backtesting',
            'live': 'live',
            'optimize': 'optimization'
        }
        
        strategy_type = type_mapping.get(template_type.lower())
        if not strategy_type:
            logger.error(f"Unknown template type: {template_type}")
            logger.info(f"Available types: {', '.join(type_mapping.keys())}")
            return False
        
        # Ensure directories exist
        strategy_dir = self.strategies_dir / strategy_type
        strategy_dir.mkdir(parents=True, exist_ok=True)
        
        # Template file
        template_file = self.templates_dir / f"{strategy_type}_template.py"
        if not template_file.exists():
            logger.warning(f"Template not found: {template_file}")
            logger.info("Creating basic template...")
            template_content = self._get_basic_template(strategy_type)
        else:
            with open(template_file, 'r') as f:
                template_content = f.read()
        
        # Create new strategy file
        new_file = strategy_dir / f"{name}.py"
        if new_file.exists():
            logger.error(f"Strategy already exists: {new_file}")
            return False
        
        with open(new_file, 'w') as f:
            f.write(template_content.replace('Template', name.replace('_', ' ').title()))
        
        logger.info(f"Created new strategy: {new_file}")
        logger.info(f"Edit the file and run: python run.py {new_file.relative_to(self.project_root)}")
        return True
    
    def _get_basic_template(self, strategy_type: str) -> str:
        """Get a basic template for strategy type"""
        if strategy_type == 'screening':
            return '''"""
Custom Screening Strategy
"""
from screener.basic_filter import BasicInfoScreener
from screener.screening_criteria import ScreeningCriteria
import logging

logger = logging.getLogger(__name__)

def run():
    """Main screening logic"""
    logger.info("Running custom screening strategy...")
    
    # Initialize screener
    screener = BasicInfoScreener()
    
    # Get S&P 500 stocks
    stocks = screener.get_snp500_basic_info()
    logger.info(f"Total stocks: {len(stocks)}")
    
    # Define your criteria here
    criteria = ScreeningCriteria(
        min_price=10,
        max_price=500,
        min_volume=500_000,
        min_market_cap=5_000_000_000,
        sectors=['Technology', 'Healthcare']
    )
    
    # Apply filters
    filtered = screener.apply_basic_filters(stocks, criteria)
    logger.info(f"Filtered stocks: {len(filtered)}")
    
    # Add your custom logic here
    # ...
    
    return filtered

if __name__ == "__main__":
    results = run()
    print(f"Found {len(results)} stocks matching criteria")
'''
        elif strategy_type == 'backtesting':
            return '''"""
Custom Backtesting Strategy
"""
from engine.backtrader_engine import BacktraderEngine
from engine.backtrader_strategy import BottomBreakoutStrategy
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def run():
    """Main backtesting logic"""
    logger.info("Running custom backtesting strategy...")
    
    # Define symbols to test
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    # Initialize backtest engine
    engine = BacktraderEngine(initial_cash=100000, commission=0.001)
    
    # Define strategy parameters
    strategy_params = {
        'lookback_days': 20,
        'breakout_threshold': 1.05,
        'stop_loss_threshold': 0.95,
        'take_profit_threshold': 1.10,
        'position_size': 0.2
    }
    
    # Set date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Run backtest
    results = engine.batch_backtest(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        strategy_class=BottomBreakoutStrategy,
        strategy_params=strategy_params
    )
    
    # Process results
    for result in results:
        if 'error' not in result:
            logger.info(f"{result['symbol']}: Return={result['total_return_pct']:.2f}%")
    
    return results

if __name__ == "__main__":
    results = run()
    print(f"Backtested {len(results)} symbols")
'''
        else:
            return '''"""
Custom Strategy
"""
import logging

logger = logging.getLogger(__name__)

def run():
    """Main strategy logic"""
    logger.info("Running custom strategy...")
    
    # Add your strategy logic here
    results = {}
    
    return results

if __name__ == "__main__":
    results = run()
    print("Strategy completed")
'''


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run trading strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py scripts/screening/tech_breakout.py
  python run.py scripts/backtesting/momentum.py --output csv
  python run.py --list
  python run.py --new screening my_value_screen
        """
    )
    
    parser.add_argument('strategy', nargs='?', help='Path to strategy file')
    parser.add_argument('--output', choices=['csv', 'json'], help='Output format for results')
    parser.add_argument('--list', action='store_true', help='List available strategies')
    parser.add_argument('--new', nargs=2, metavar=('TYPE', 'NAME'),
                       help='Create new strategy from template')
    
    args = parser.parse_args()
    
    runner = StrategyRunner()
    
    if args.list:
        runner.list_strategies()
    elif args.new:
        template_type, name = args.new
        runner.create_from_template(template_type, name)
    elif args.strategy:
        success = runner.run_strategy(args.strategy, args.output)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()