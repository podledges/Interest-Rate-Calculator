from quant.day_counter import calculate_year_fraction
from dateutil.relativedelta import relativedelta
from cubic_spline import CubicSplineCurve 

import matplotlib.pyplot as plt
import datetime
import numpy as np

class FuturesCurveBuilder:
    def __init__(self, market_data, config):
        self.market_data = market_data
        self.config = config
        
        self.trade_date = datetime.datetime.strptime(config['trade_date'], "%d-%m-%Y").date()
        self.convention = config['day_count_convention']
        self.freq = config['payment_frequency']
        self.interpolation_method = config['interpolation_method']
        
        # T=0 always has a discount factor of 1.0
        self.discount_factors = {0.0: 1.0}

    def build_curve(self):
        self._process_cash_rates()
        self._process_futures()
        self._process_swaps()
        return self.discount_factors
    
    def plot_curve(self, plot_type='zero_rate'):
        """Plots the yield curve using CubicSplineCurve over verified knots."""
        if not self.discount_factors:
            print("No curve data to display. Execute build_curve() first.")
            return

        # 1. Extract sorted times and corresponding discount factors
        times = np.array(sorted(self.discount_factors.keys()))
        dfs = np.array([self.discount_factors[t] for t in times])

        # 2. Generate smooth points for plotting the continuous line
        times_smooth = np.linspace(times.min(), times.max(), 500)

        plt.figure(figsize=(10, 6))

        if plot_type == 'zero_rate':
            # Calculate zero rates, handling T=0 to avoid division by zero
            rates = np.array([
                0.0 if t == 0 else (-np.log(df) / t) * 100 for t, df in zip(times, dfs)
            ])

            if len(times) >= 3:
                curve = CubicSplineCurve(times, rates)
                rates_smooth = curve.evaluate(times_smooth)
                plt.plot(times_smooth, rates_smooth, '-', color='b', label='Smoothed Spline Zero Curve')
            else:
                plt.plot(times, rates, '--', color='b', label='Linear Zero Curve')

            plt.scatter(times, rates, color='red', zorder=5, label='Bootstrapped Knots')
            plt.ylabel('Continuous Zero Rate (%)', fontsize=12)
            plt.title('Zero-Coupon Yield Curve', fontsize=14, fontweight='bold')

        elif plot_type == 'discount_factor':
            if len(times) >= 3:
                curve = CubicSplineCurve(times, dfs)
                dfs_smooth = curve.evaluate(times_smooth)
                plt.plot(times_smooth, dfs_smooth, '-', color='g', label='Smoothed Spline DF Curve')
            else:
                plt.plot(times, dfs, '--', color='g', label='Linear DF Curve')

            plt.scatter(times, dfs, color='red', zorder=5, label='Bootstrapped Knots')
            plt.ylabel('Discount Factor D(0, T)', fontsize=12)
            plt.title('Discount Factor Curve', fontsize=14, fontweight='bold')

        plt.xlabel('Time (Years)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.show()

    def _process_cash_rates(self):
        cash_data = [d for d in self.market_data if d['type'] == 'Cash']
        
        for item in cash_data:
            t = calculate_year_fraction(self.trade_date, item['maturity_date'], self.convention)
            df = 1.0 / (1.0 + item['rate'] * t)
            self.discount_factors[t] = df

    def _process_futures(self):
        futures_data = [d for d in self.market_data if d['type'] == 'Future']
        futures_data.sort(key=lambda x: x['start_date'])
        
        for item in futures_data:
            t_start = calculate_year_fraction(self.trade_date, item['start_date'], self.convention)
            t_end = calculate_year_fraction(self.trade_date, item['maturity_date'], self.convention)
            
            # The duration of the future in years
            tau = t_end - t_start 
            implied_forward_rate = (100.0 - item['price']) / 100.0
            
            if t_start in self.discount_factors:
                df_start = self.discount_factors[t_start]
                df_end = df_start / (1.0 + implied_forward_rate * tau)
                self.discount_factors[t_end] = df_end
            else:
                # If t_start does not perfectly align with a previously calculated grid point,
                # you must interpolate the discount curve to find df_start here.
                pass

    def _process_swaps(self):
        swap_data = [d for d in self.market_data if d['type'] == 'Swap']
        swap_data.sort(key=lambda x: x['maturity_date'])
        
        for item in swap_data:
            mat_date = item['maturity_date']
            t_maturity = calculate_year_fraction(self.trade_date, mat_date, self.convention)
            par_rate = item['rate']
            
            # Using the analytical bootstrap logic you provided
            schedule = self._generate_forward_schedule(mat_date)
            running_coupon_pv = 0.0
            prev_date = self.trade_date
            
            for current_date in schedule[:-1]:
                t_i = calculate_year_fraction(self.trade_date, current_date, self.convention)
                tau_i = calculate_year_fraction(prev_date, current_date, self.convention)
                
                # Fetch or interpolate the discount factor
                df_i = self._get_discount_factor(t_i)
                
                running_coupon_pv += tau_i * df_i
                prev_date = current_date
                
            tau_n = calculate_year_fraction(prev_date, mat_date, self.convention)
            
            numerator = 1.0 - (par_rate * running_coupon_pv)
            denominator = 1.0 + (par_rate * tau_n)
            final_df = numerator / denominator
            
            self.discount_factors[t_maturity] = final_df

    def _get_discount_factor(self, t):
        """Continuous getter that applies zero-rate interpolation for missing nodes."""
        if t in self.discount_factors:
            return self.discount_factors[t]
        
        # Convert all known DFs to zero rates for smooth interpolation
        known_times = sorted(self.discount_factors.keys())
        # Prevent division by zero for T=0
        zero_rates = [
            0.0 if t_known == 0 else -np.log(self.discount_factors[t_known]) / t_known 
            for t_known in known_times
        ]
        
        # Stolen and adapted interpolation logic
        interpolated_zero = float(np.interp(t, known_times, zero_rates))
        
        # Convert back to discount factor
        return np.exp(-interpolated_zero * t)

    def _generate_forward_schedule(self, maturity_date):
        """Stolen directly from curve_builder.py"""
        months_step = int(12 / self.freq)
        schedule = []
        current_date = maturity_date
        while current_date > self.trade_date:
            schedule.append(current_date)
            current_date -= relativedelta(months=months_step)
        schedule.reverse()
        return schedule
