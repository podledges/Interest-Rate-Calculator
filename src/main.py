import datetime

# --- IMPORT FUNCTIONS ---
from src.quant.day_counter import calculate_year_fraction
from src.quant.discount_factor import calculate_discount_factor, calculate_df_from_dates
from src.engine.schedule import generate_payment_schedule # (Assuming you put this in engine)

def main():
    print("=== SWAP CALCULATOR QUICK-TEST SANDBOX ===\n")
    
    # ---------------------------------------------------------
    #                 CONFIGURE ME
    # ---------------------------------------------------------
    d_start = datetime.date(1990, 5, 17)
    d_end = datetime.date(1990, 6, 17)
    
    swap_maturity = datetime.date(1993, 11, 1)
    
    test_rate = 0.094765
    test_convention = "ACT/360"
    
    
    # ---------------------------------------------------------
    # DAY COUNTER
    # ---------------------------------------------------------
    # fraction = calculate_year_fraction(d_start, d_end, test_convention)
    # print(f"[Day Counter] Year Fraction: {fraction:.6f}")
    
    
    # ---------------------------------------------------------
    # DISCOUNT FACTOR                               [standalone]
    # PARAMS: RATE, TIME FRACTION
    # ---------------------------------------------------------
    # pure_df = calculate_discount_factor(rate=test_rate, time_fraction=0.086111)
    # print(f"[Pure DF] Discount Factor: {pure_df:.6f}")
    
    
    # ---------------------------------------------------------
    # DISCOUNT FACTOR                               [integrated]
    # PARAMS: RATE, date Start, date End, Convention
    # ---------------------------------------------------------
    integrated_df = calculate_df_from_dates(test_rate, d_start, d_end, test_convention)
    print(f"[Integrated DF] Discount Factor: {integrated_df:.6f}")
    


if __name__ == "__main__":
    main()