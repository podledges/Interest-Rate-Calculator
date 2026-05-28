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
    
    # ---------------------------------------------------------
    #                 CONFIGURE ME
    # ---------------------------------------------------------
    

    # Ensure Python can find your 'src' directory
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))

    # Import your custom classes
    # Adjust the import paths if your fi

def run_curve_pipeline():
    print("--- Starting Yield Curve Pipeline ---")
    
    # 1. Initialize the Parser
    # Update these paths if your csv/json are stored in a different folder
    parser = DataParser(data_path="src/data/data.csv", config_path="src/data/config.json")
    
    # 2. Load the Data
    parser.load_configuration()
    parser.load_market_data()
    
    # Safety check before proceeding
    if parser.curve_data.empty or not parser.settings:
        print("Error: Pipeline halted due to missing data or configuration.")
        return

    print("\n--- Initializing Curve Builder ---")
    # 3. Instantiate the Builder using the parsed data
    builder = CurveBuilder(market_data_df=parser.curve_data, config=parser.settings)
    
    # 4. Execute the mathematical bootstrapping
    try:
        builder.build_swap_curve()
        print("Bootstrapping complete. Zero rates calculated successfully.")
    except Exception as e:
        print(f"Error during bootstrapping: {e}")
        return
        
    # 5. Visualize the result
    print("Generating plot...")
    builder.plot_curve()

def run_curve_builder_w_futures(market_data, config, plot_type='zero_rate'):
    """
    Initializes the FuturesCurveBuilder, calculates the discount factors, 
    and generates the requested plot.
    """
    # 1. Instantiate the builder
    builder = FuturesCurveBuilder(market_data, config)

    # 2. Build the math (calculates the points)
    discount_factors = builder.build_curve()
    
    # 3. Plot the results (renders the visual)
    builder.plot_curve(plot_type=plot_type)
    
    # Optional: Return the calculated data if you need to use it elsewhere in your script
    return discount_factors

if __name__ == "__main__":
    run_curve_pipeline()
    # run_curve_builder_w_futures()     -- MIGHT OR MIGHT NOT WORK

# if __name__ == "__main__":
#     main()