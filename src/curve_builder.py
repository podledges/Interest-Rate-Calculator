import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import matplotlib.pyplot as plt

# Importing from your project structure
from src.quant.day_counter import calculate_year_fraction
from src.cubic_spline import CubicSplineCurve 

class CurveBuilder:
    def __init__(self, market_data_df, config):
        self.market_data = market_data_df
        self.config = config
        
        # Parse global settings from JSON
        # FIXED: Format changed to %d-%m-%Y to match "17-05-1990" in config.json
        self.trade_date = datetime.datetime.strptime(config['trade_date'], "%d-%m-%Y").date()
        self.convention = config['day_count_convention']
        self.freq = config['payment_frequency']
        self.interp_method = config['interpolation_method']
        
        self.zero_rates = []  # Stores the final calculated curve

    def build_swap_curve(self):
        """The main pipeline: Filter -> Interpolate Gaps -> Bootstrap."""
        swap_data = self.market_data[self.market_data['Instrument'] == 'Swap'].copy()
        
        # 1. Convert string tenors to exact maturity dates and fractional years
        swap_data['MaturityDate'] = swap_data['Tenor'].apply(self._tenor_to_date)
        swap_data['TimeInYears'] = swap_data['MaturityDate'].apply(
            lambda d: calculate_year_fraction(self.trade_date, d, self.convention)
        )
        
        # 2. Pre-process: Fill in all missing payment dates
        full_schedule_years, full_schedule_rates = self._fill_missing_tenors(
            known_years=swap_data['TimeInYears'].values,
            known_rates=swap_data['Rate'].values
        )
        
        # 3. Process: Bootstrap the completed grid
        for i in range(len(full_schedule_years)):
            self._bootstrap_swap(
                time_in_years=full_schedule_years[i], 
                par_rate=full_schedule_rates[i]
            )

    def _fill_missing_tenors(self, known_years, known_rates):
        """Generates a perfectly spaced grid of rates based on the payment frequency."""
        max_year = max(known_years)
        step = 1.0 / self.freq
        
        required_years = np.arange(step, max_year + step, step)
        
        if self.interp_method.lower() == 'cubic_spline':
            spline = CubicSplineCurve(known_years, known_rates)
            # FIXED: Called .evaluate() to match the CubicSplineCurve class definition
            interpolated_rates = spline.evaluate(required_years)
        elif self.interp_method.lower() == 'linear':
            interpolated_rates = np.interp(required_years, known_years, known_rates)
        else:
            raise ValueError(f"Unsupported interpolation method: {self.interp_method}")
            
        return required_years, interpolated_rates

    def _bootstrap_swap(self, time_in_years, par_rate):
        """
        Bootstraps a single swap rate assuming all prior zero rates are known.
        """
        coupon_payment = par_rate / self.freq
        sum_of_prior_dfs = 0.0
        
        # Retrieve previously calculated discount factors for the summation
        for stored_point in self.zero_rates:
            if stored_point['time_in_years'] < time_in_years:
                sum_of_prior_dfs += stored_point['discount_factor']
                
        # Forward substitution algebra
        numerator = 1.0 - (coupon_payment * sum_of_prior_dfs)
        denominator = 1.0 + coupon_payment
        final_discount_factor = numerator / denominator
        
        # Convert to continuous zero rate
        zero_rate = -np.log(final_discount_factor) / time_in_years
        
        self.zero_rates.append({
            'time_in_years': time_in_years,
            'discount_factor': final_discount_factor,
            'zero_rate': zero_rate
        })

    def _tenor_to_date(self, tenor_str):
        """Helper to convert standard market strings ('5Y', '1W', 'O/N') into exact dates."""
        tenor_str = tenor_str.upper().strip()
        
        if tenor_str == 'O/N': 
            return self.trade_date + relativedelta(days=1)
        elif tenor_str == 'S/N' or tenor_str == 'SPOT': 
            return self.trade_date + relativedelta(days=2)
            
        try:
            value = int(tenor_str[:-1])
            unit = tenor_str[-1]
            
            if unit == 'Y':
                return self.trade_date + relativedelta(years=value)
            elif unit == 'M':
                return self.trade_date + relativedelta(months=value)
            elif unit == 'W':
                return self.trade_date + relativedelta(weeks=value)
            elif unit == 'D':
                return self.trade_date + relativedelta(days=value)
            else:
                raise ValueError(f"Unknown tenor unit: {unit}")
                
        except ValueError:
            print(f"Error parsing tenor: {tenor_str}. Defaulting to trade date.")
            return self.trade_date
            
    def plot_curve(self):
        """Plots the calculated zero-coupon yield curve."""
        if not self.zero_rates:
            print("No curve data to plot. Run build_swap_curve() first.")
            return
            
        times = [pt['time_in_years'] for pt in self.zero_rates]
        rates = [pt['zero_rate'] * 100 for pt in self.zero_rates] 
        
        plt.figure(figsize=(10, 6))
        plt.plot(times, rates, marker='o', linestyle='-', color='b', label='Zero Curve')
        plt.title('Bootstrapped Zero-Coupon Yield Curve')
        plt.xlabel('Time (Years)')
        plt.ylabel('Continuous Zero Rate (%)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.show()