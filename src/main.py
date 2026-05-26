import datetime

from src.quant.day_counter import calculate_year_fraction
from src.quant.discount_factor import calculate_discount_factor, calculate_df_from_dates
from src.quant.stub_factor import interpolate_stub_rates_linearly, calculate_stub_present_value
from src.quant.annuity import calculate_annuity_present_value
def main():
    print("Test Branch")
    print("=== SWAP CALCULATOR QUICK-TEST SANDBOX ===\n")
    
    # ---------------------------------------------------------
    #                 CONFIGURE ME
    # ---------------------------------------------------------
        
    present_date = datetime.date(1990,5,1)
    start_date = datetime.date(1990, 5, 17)
    maturity_date = datetime.date(1993, 11, 1)
    
    test_rate = 0.094765
    test_convention = "ACT/360"     #available conventions: 30/360, EQUAL, ACT/360, ACT/365
    
    #notional, issue fee, issue priceless fee 
    notional_principal = 10_000_000

    # Bond issuing ?????? 
    issue_price_rate = 1.0
    issue_fee_rate:float = 1 + (7/8)        #check if there is any weird float explicit declaraiton
    issue_price_less_fee = issue_price_rate - issue_fee_rate

    # Disocunt


    # ====================    DAY COUNTER     ====================
    # fraction = calculate_year_fraction(d_start, d_end, test_convention)
    # print(f"[Day Counter] Year Fraction: {fraction:.6f}")
    
    
    # ====================    Discount Factor     ====================
    # pure_df = calculate_discount_factor(rate=test_rate, time_fraction=0.086111)
    # print(f"[Pure DF] Discount Factor: {pure_df:.6f}")

    # PARAMS: RATE, date Start, date End, Convention
    integrated_df = calculate_df_from_dates(test_rate, start_date, maturity_date, test_convention)
    print(f"[Integrated DF] Discount Factor: {integrated_df:.6f}")

    # ====================    DECOMPOUNDED RATE     ====================
    # new_rate = 



    # ====================    STUB DATES   ====================
    #params: 

    #present value of stub either use
    stub_pv = calculate_stub_present_value(notional_principal,
                                            start_date,   #start date??? 
                                            point1=(4-1-1990,0.4),  #interpolation between this date 
                                            point2=(4-1-1993,0.43),      #and this date
                                            basis="ACT/360")
    print(stub_pv)
    
    # ====================    ANNUITY   ====================
    #
    annuity_pv = calculate_annuity_present_value(regular_payment= 500_000,
                                                 num_of_payments_left=3,
                                                 discount_rate=0.67)
    
    # ====================    SWAP CALCULATOR   ====================
    #FLOATING LEG CALCULATION, FIXED LEG CALCULATOIN
    #Present value of a basic swap = stub_pv + annuity_pv

if __name__ == "__main__":
    main()