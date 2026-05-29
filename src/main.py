import sys
import os

# Go up one level from 'src' to the root project folder and add it to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Now Python can safely find the 'src' folder
from src.data.csv_to_py import DataParser
from curve_builder import CurveBuilder
from futures_curve_builder import FuturesCurveBuilder
# from src.quant.day_counter import calculate_year_fraction
# from src.quant.discount_factor import calculate_discount_factor, calculate_df_from_dates
# from src.quant.stub_factor import interpolate_stub_rates_linearly, calculate_stub_present_value
# from src.quant.annuity import calculate_annuity_present_value
# from src.quant.forward_rate import solve_forward_rate_variables

def main():
    print("=== SWAP CALCULATOR QUICK-TEST SANDBOX ===\n")

    # Ensure Python can find your 'src' directory
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def run_curve_pipeline(with_futures = False):
    print("--- Starting Yield Curve Pipeline ---")
    
    parser = DataParser(data_path="src/data/real-data.csv", config_path="src/data/config.json")
    
    parser.load_configuration()
    parser.load_market_data()
    
    if parser.curve_data.empty or not parser.settings:
        print("Error: Pipeline halted due to missing data or configuration.")
        return
    
    market_data = parser.curve_data
    config = parser.settings
    
    if with_futures:
        print("\n--- Initializing Curve Builder (with Futures) ---")
        builder = FuturesCurveBuilder(market_data, config)
    else:
        print("\n--- Initializing Curve Builder ---")
        builder = CurveBuilder(market_data, config)
        
    try:
        builder.build_curve()
        discount_factors = builder.build_curve()
    except Exception as e:
        print(f"Error during bootstrapping: {e}")
        return

    print("Generating plot...")
    builder.plot_curve()

    return discount_factors

if __name__ == "__main__":
    run_curve_pipeline(True)
    # run_curve_builder_w_futures()