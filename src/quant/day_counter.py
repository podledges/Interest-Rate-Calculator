import datetime
import calendar
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
            
    else:
        raise ValueError(f"Unsupported day count convention: {convention}")



def calculate_time_passed(date1:datetime.date, date2:datetime.date):
    """
    Returns years, months, and days between two dates.
    Automatically determines which one is date1 and which is date2
    """
    if date1 > date2:
        start_date = date2
        end_date = date1
    else:
        start_date = date1
        end_date = date2

    years = end_date.year - start_date.year
    months = end_date.month - start_date.month
    days = end_date.day - start_date.day

    if days < 0:
        prev_month = end_date.month - 1 if end_date.month > 1 else 12
        prev_year = end_date.year if end_date.month > 1 else end_date.year - 1
        _, days_in_prev_month = calendar.monthrange(prev_year, prev_month)
        
        days += days_in_prev_month
        months -= 1

    if months < 0:
        months += 12
        years -= 1

    return (years, months, days)



if __name__ == "__main__":
    date_start = datetime.date(2024, 2, 15)
    date_end = datetime.date(2024, 3, 15)
    
    years,months,days = calculate_time_passed(date_start,date_end)
    print(f"Time passed: {years} years, {months} months, and {days} days.")    
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