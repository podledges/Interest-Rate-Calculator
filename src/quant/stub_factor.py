import datetime

from src.quant.day_counter import calculate_year_fraction
from src.quant.day_counter import calculate_time_passed
from src.quant.discount_factor import calculate_discount_factor
from typing import Optional

#def calculate_stub_rate(benchmark_rate: float, days: int, basis:str):
 ##  return 1 + (benchmark_rate * days)

def interpolate_stub_rates_linearly(target_date: datetime.date, point1: tuple[datetime.date, float], 
                                    point2: tuple[datetime.date, float], basis: str, frequency: Optional[int] = None)-> float:
    """
    Linearly interpolates a rate for an irregular target date.
    point1 : Tuple of (date1, rate1) representing the lower market bound
    point2 : Tuple of (date2, rate2) representing the upper market bound
    basis  : The day count convention basis (e.g., 360 or 365)
    """
    date1, rate1 = point1
    date2, rate2 = point2
    
    t1 = 0.0
    t_target = calculate_year_fraction(date1, target_date, basis, frequency)
    t2 = calculate_year_fraction(date1, date2, basis)
    
    time_ratio = (t_target - t1) / (t2 - t1)
    
    interpolated_rate = rate1 + (rate2 - rate1) * time_ratio
    return interpolated_rate

def calculate_stub_present_value(notional:int, target_date: datetime.date, point1: tuple[datetime.date, float], 
                                    point2: tuple[datetime.date, float], basis: str, frequency: Optional[int] = None):
    
    rate = interpolate_stub_rates_linearly(target_date, point1, point2, basis, frequency)
    start_date, rate1 = point1
    end_date, rate2 = point2
    time_fraction = calculate_year_fraction(start_date,end_date,basis,frequency)
    discount_rate = calculate_discount_factor(rate, time_fraction)
    return discount_rate * notional
 

if __name__ == "__main__":
    three_year_point = (datetime.date(2029, 5, 21), 0.0420)
    four_year_point  = (datetime.date(2030, 5, 21), 0.0450)

    stub_payment_date = datetime.date(2029, 7, 21)

    r_benchmark = interpolate_stub_rates_linearly(
        stub_payment_date, 
        three_year_point, 
        four_year_point, 
        basis="ACT/360"
    )
    print(r_benchmark)

