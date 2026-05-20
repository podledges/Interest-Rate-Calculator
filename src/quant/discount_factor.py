import datetime
# Absolute import from your project root
from src.quant.day_counter import calculate_year_fraction

def calculate_discount_factor(rate: float, time_fraction: float) -> float:
    """
    Pure Math: Calculates the present value of $1 received at a specific future time.
    
    Args:
        rate: The annualized discount rate as a decimal.
        time_fraction: The time until payment, expressed in years.
    """
    if rate <= -1.0:
        raise ValueError("Interest rate cannot be <= -100%.")
        
    return 1.0 / ((1.0 + rate) ** time_fraction)

def calculate_df_from_dates(
    rate: float, 
    start_date: datetime.date, 
    end_date: datetime.date, 
    convention: str,
    frequency: int = None
) -> float:
    """
    Integration: Bridges the calendar logic with the financial math.
    Automatically calculates the day count fraction and returns the discount factor.
    """
    # 1. Get the exact fractional year from your day counter library
    t = calculate_year_fraction(start_date, end_date, convention, frequency)
    
    # 2. Feed that fraction into the pure discounting formula
    return calculate_discount_factor(rate, time_fraction=t)


# --- Execution and Proof Block ---
if __name__ == "__main__":
    print("--- Testing Integrated Discounting ---")
    
    test_rate = 0.094765
    d_start = datetime.date(1990, 5, 17)
    d_end = datetime.date(1990, 6, 17)
    
    try:
        # We can now just call the wrapper function directly
        df = calculate_df_from_dates(
            rate=test_rate, 
            start_date=d_start, 
            end_date=d_end, 
            convention="ACT/360"
        )
        print(f"Discount Factor for 1-month period: {df:.6f}")
        
    except Exception as e:
        print(f"Test Failed! Error: {e}")