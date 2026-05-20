import datetime
from typing import Optional

def calculate_year_fraction(start_date: datetime.date, end_date: datetime.date, convention: str, frequency: Optional[int] = None) -> float:
    """
    Calculates the fractional day count between two dates 
    based on 4 differents basis conventions. (ACT/365, ACT/360, 30/360, EQUAL).
    """

    convention = convention.upper().strip()
    
    if convention == "EQUAL":
        if frequency is None or frequency <= 0:
            raise ValueError("The 'EQUAL' coupon convention requires a valid positive integer frequency.")
        return 1.0 / float(frequency)
            
    elif convention == "ACT/365":
        actual_days = (end_date - start_date).days
        return actual_days / 365.0
            
    elif convention == "ACT/360":
        actual_days = (end_date - start_date).days
        return actual_days / 360.0
            
    elif convention == "30/360":
        y1, m1, d1 = start_date.year, start_date.month, start_date.day
        y2, m2, d2 = end_date.year, end_date.month, end_date.day
            
        if d1 == 31:
            d1 = 30
        if d2 == 31 and d1 >= 30:
            d2 = 30
            
        calculated_days = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)
        return calculated_days / 360.0
            
    else:       # ERROR MSG
        raise ValueError(f"Unsupported day count convention: {convention}")



if __name__ == "__main__":
    date_start = datetime.date(2024, 2, 15)
    date_end = datetime.date(2024, 3, 15)
    
    print("--- Testing Leap Year Intervals (Feb 15 to Mar 15, 2024) ---")
    
    # ACT/360 will naturally capture 29 days in the numerator
    act360_frac = calculate_year_fraction(date_start, date_end, "ACT/360")
    print(f"ACT/360 Year Fraction: {act360_frac:.6f}")
    
    # 30/360 will treat the interval as exactly 30 days long
    bond30360_frac = calculate_year_fraction(date_start, date_end, "30/360")
    print(f"30/360  Year Fraction: {bond30360_frac:.6f}")
    
    # EQUAL convention completely bypasses dates to return a flat frequency chunk
    equal_frac = calculate_year_fraction(date_start, date_end, "EQUAL", frequency=2)
    print(f"EQUAL (Semi-Annual) Frac: {equal_frac:.6f}")