import sys
import os

# Go up one level from 'src' to the root project folder and add it to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Now Python can safely find the 'src' folder
from src.data.csv_to_py import DataParser
from src.curve_builder import CurveBuilder
from src.quant.day_counter import calculate_year_fraction
from src.quant.discount_factor import calculate_discount_factor, calculate_df_from_dates
from src.quant.stub_factor import interpolate_stub_rates_linearly, calculate_stub_present_value
from src.quant.annuity import calculate_annuity_present_value
from src.quant.forward_rate import solve_forward_rate_variables
def main():
    print("=== SWAP CALCULATOR QUICK-TEST SANDBOX ===\n")
    
    # ---------------------------------------------------------
    #                 CONFIGURE ME
    # ---------------------------------------------------------
    

    # Ensure Python can find your 'src' directory
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))

    # Import your custom classes
    # Adjust the import paths if your file names differ slightly
    from src.data.csv_to_py import MarketDataParser
    from src.curve_builder import CurveBuilder

    def run_curve_pipeline():
        print("--- Starting Yield Curve Pipeline ---")
        
        # 1. Initialize the Parser
        # Update these paths if your csv/json are stored in a different folder
        parser = MarketDataParser(data_path="data.csv", config_path="config.json")
        
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

    if __name__ == "__main__":
        run_curve_pipeline()




    
    # present_date = datetime.date(1990,5,1)
    # start_date = datetime.date(1990, 5, 17)
    # maturity_date = datetime.date(1993, 11, 1)
    
    # test_rate = 0.094765
    # test_convention = "ACT/360"     #available conventions: 30/360, EQUAL, ACT/360, ACT/365
    
    # #notional, issue fee, issue priceless fee 
    # notional_principal = 10_000_000

    # # Bond issuing ?????? 
    # issue_price_rate = 1.0
    # issue_fee_rate:float = 1 + (7/8)        #check if there is any weird float explicit declaraiton
    # issue_price_less_fee = issue_price_rate - issue_fee_rate

    # # Disocunt


    # # ====================    DAY COUNTER     ====================
    # # fraction = calculate_year_fraction(d_start, d_end, test_convention)
    # # print(f"[Day Counter] Year Fraction: {fraction:.6f}")
    
    
    # # ====================    Discount Factor     ====================
    # # pure_df = calculate_discount_factor(rate=test_rate, time_fraction=0.086111)
    # # print(f"[Pure DF] Discount Factor: {pure_df:.6f}")

    # # PARAMS: RATE, date Start, date End, Convention
    # integrated_df = calculate_df_from_dates(test_rate, start_date, maturity_date, test_convention)
    # print(f"[Integrated DF] Discount Factor: {integrated_df:.6f}")

    # # ====================    DECOMPOUNDED RATE     ====================
    # # new_rate = 

    # # ====================    FORWARD RATE VARIABLES ===================
    # #F1 = DISCOUNT factor at D1. 
    # answer = solve_forward_rate_variables(F1-None, 
    #                              F2- None,
    #                              forward_rate = None,
    #                              days= None,
    #                              basis = int)
    # print(answer)

    # # ====================    STUB DATES   ====================
    # #params: 

    # #present value of stub either use
    # stub_pv = calculate_stub_present_value(notional_principal,
    #                                         start_date,   #start date??? 
    #                                         point1=(4-1-1990,0.4),  #interpolation between this date 
    #                                         point2=(4-1-1993,0.43),      #and this date
    #                                         basis="ACT/360")
    # print(stub_pv)
    
    # # ====================    ANNUITY   ====================
    # #
    # annuity_pv = calculate_annuity_present_value(regular_payment= 500_000,
    #                                              num_of_payments_left=3,
    #                                              discount_rate=0.67)
    
    # ====================    SWAP CALCULATOR   ====================
    #FLOATING LEG CALCULATION, FIXED LEG CALCULATOIN
    #Present value of a basic swap = stub_pv + annuity_pv

# if __name__ == "__main__":
#     main()