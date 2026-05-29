from quant.day_counter import calculate_year_fraction
from dateutil.relativedelta import relativedelta
from cubic_spline import CubicSplineCurve 

from scipy.interpolate import pchip_interpolate

import calendar
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
        for idx, row in self.market_data.iterrows():
            if row['Instrument'] == 'Future':
                start, mat = self._parse_future_tenor(row['Tenor'])
                self.market_data.at[idx, 'start_date'] = start
                self.market_data.at[idx, 'MaturityDate'] = mat
            else:
                self.market_data.at[idx, 'start_date'] = self.trade_date
                self.market_data.at[idx, 'MaturityDate'] = self._tenor_to_date(row['Tenor'])

        self.market_data['Quote'] = self.market_data['Quote'].astype(float)

        self._process_cash_rates()
        self._process_futures()
        self._process_swaps()

        self.print_discount_factors()

        return self.discount_factors
    
    def _process_cash_rates(self):
        cash_df = self.market_data[self.market_data['Instrument'] == 'Cash']
        cash_data = cash_df.to_dict('records')

        cash_data.sort(key=lambda x: x['MaturityDate'])
        
        for item in cash_data:
            decimal_rate = item['Quote'] / 100.0
            t = calculate_year_fraction(self.trade_date, item['MaturityDate'], self.convention)
            df = 1.0 / (1.0 + decimal_rate * t)
            self.discount_factors[t] = df

    def _process_futures(self):
        futures_df = self.market_data[self.market_data['Instrument'] == 'Future']
        futures_data = futures_df.to_dict('records')
        
        futures_data.sort(key=lambda x: x['start_date'])
        
        for item in futures_data:
            t_start = calculate_year_fraction(self.trade_date, item['start_date'], self.convention)
            t_end = calculate_year_fraction(self.trade_date, item['MaturityDate'], self.convention)
            
            tau = t_end - t_start 
            implied_forward_rate = (100.0 - item['Quote']) / 100.0
            
            if t_start in self.discount_factors:
                df_start = self.discount_factors[t_start]
                df_end = df_start / (1.0 + implied_forward_rate * tau)
                self.discount_factors[t_end] = df_end
            else:
                df_start = self._get_discount_factor(t_start)
                df_end = df_start / (1.0 + implied_forward_rate * tau)
                self.discount_factors[t_end] = df_end

    def _process_swaps(self):
        swap_df = self.market_data[self.market_data['Instrument'] == 'Swap']
        swap_data = swap_df.to_dict('records')
        
        swap_data.sort(key=lambda x: x['MaturityDate'])
        
        for item in swap_data:
            mat_date = item['MaturityDate']
            t_maturity = calculate_year_fraction(self.trade_date, mat_date, self.convention)
            par_rate = item['Quote'] / 100.0
            
            schedule = self._generate_forward_schedule(mat_date)
            running_coupon_pv = 0.0
            prev_date = self.trade_date
            
            for current_date in schedule[:-1]:
                t_i = calculate_year_fraction(self.trade_date, current_date, self.convention)
                tau_i = calculate_year_fraction(prev_date, current_date, self.convention)
                
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
        
        interpolated_zero = float(np.interp(t, known_times, zero_rates))
        
        return np.exp(-interpolated_zero * t)
    
    def _tenor_to_date(self, tenor_str):
        tenor_str = tenor_str.upper().strip()
        if tenor_str in ('O/N', 'OVERNIGHT'): return self.trade_date + relativedelta(days=1)
        try:
            value = int(tenor_str[:-1])
            unit = tenor_str[-1]
            if unit == 'Y': return self.trade_date + relativedelta(years=value)
            elif unit == 'M': return self.trade_date + relativedelta(months=value)
            elif unit == 'W': return self.trade_date + relativedelta(weeks=value)
            elif unit == 'D': return self.trade_date + relativedelta(days=value)
            else: raise ValueError(f"Unknown unit: {unit}")
        except ValueError: raise ValueError(f"Error parsing tenor string: {tenor_str}")


    def _parse_future_tenor(self, tenor_str):
        """
        Robustly parses a ticker like 'SR3M6' into (start_date, maturity_date).
        """
        # Clean string from any trailing spaces/newlines
        ticker = str(tenor_str).strip().upper()
        
        month_codes = {'H': 3, 'M': 6, 'U': 9, 'Z': 12}
        
        # Read backward from the end of the string to guarantee we grab the codes
        year_digit = ticker[-1]   # Last character: '6', '7', or '8'
        month_code = ticker[-2]   # Second to last character: 'H', 'M', 'U', 'Z'
        
        if month_code not in month_codes:
            raise ValueError(f"Failed to parse month code from ticker: {ticker}")
            
        month = month_codes[month_code]
        year = int(f"202{year_digit}") # Maps '6'->2026, '7'->2027, '8'->2028
        
        # Find the 3rd Wednesday
        cal = calendar.monthcalendar(year, month)
        wednesdays = [week[calendar.WEDNESDAY] for week in cal if week[calendar.WEDNESDAY] != 0]
        start_date = datetime.date(year, month, wednesdays[2])
        
        # 3 Months contract length
        maturity_date = start_date + relativedelta(months=3)
        
        return start_date, maturity_date

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

    def plot_curve(self, plot_type='zero_rate'):
        """Plots the yield curve with pseudo-log/custom scaling for uniform tenor spacing."""
        if not self.discount_factors:
            print("No curve data to display. Execute build_curve() first.")
            return

        times = np.array(sorted(self.discount_factors.keys()))
        dfs = np.array([self.discount_factors[t] for t in times])

        times_no_zero = times[1:]
        max_time = times.max()

        short_end_ticks = [1/12, 3/12, 6/12, 9/12, 1.0, 15/12, 18/12, 21/12, 2.0]
        short_end_labels = ['1M', '3M', '6M', '9M', '1Y', '15M', '18M', '21M', '2Y']
        
        long_end_ticks = list(range(3, int(np.ceil(max_time)) + 1))
        long_end_labels = [f"{y}Y" for y in long_end_ticks]
        
        milestone_ticks = np.array(short_end_ticks + long_end_ticks)
        milestone_labels = short_end_labels + long_end_labels

        # 2. Map coordinates: index positions (0, 1, 2...) will be our visual "x"
        visual_x_milestones = np.arange(len(milestone_ticks))

        # Helper function to map any arbitrary continuous time T into our uniform visual space
        def transform_to_visual_space(t_array):
            # Linearly interpolates actual times into the evenly spaced index positions
            return np.interp(t_array, milestone_ticks, visual_x_milestones)

        # Generate smooth line points directly inside the visual space sequence
        visual_x_smooth = np.linspace(0, visual_x_milestones[-1], 500)
        
        # We must map actual curve times into visual x coordinates for plotting knots
        visual_x_knots = transform_to_visual_space(times_no_zero)

        plt.figure(figsize=(11, 6))

        if plot_type == 'zero_rate':
            rates = np.array([
                0.0 if t == 0 else (-np.log(df) / t) * 100 for t, df in zip(times, dfs)
            ])
            rates_no_zero = rates[1:]

            if len(times_no_zero) >= 3:
                curve = CubicSplineCurve(times_no_zero, rates_no_zero)
                times_smooth = np.interp(visual_x_smooth, visual_x_milestones, milestone_ticks)
                rates_smooth = curve.evaluate(times_smooth)
                plt.plot(visual_x_smooth, rates_smooth, '-', color='b', label='Smoothed Spline Zero Curve')
            else:
                plt.plot(visual_x_knots, rates_no_zero, '--', color='b', label='Linear Zero Curve')

            plt.scatter(visual_x_knots, rates_no_zero, color='red', zorder=5, label='Bootstrapped Knots')
            plt.ylabel('Continuous Zero Rate (%)', fontsize=12)
            plt.title('Zero-Coupon Yield Curve (Scaled Tenors)', fontsize=14, fontweight='bold')

        elif plot_type == 'discount_factor':
            if len(times_no_zero) >= 3:
                curve = CubicSplineCurve(times_no_zero, dfs[1:])
                times_smooth = np.interp(visual_x_smooth, visual_x_milestones, milestone_ticks)
                dfs_smooth = curve.evaluate(times_smooth)
                plt.plot(visual_x_smooth, dfs_smooth, '-', color='g', label='Smoothed Spline DF Curve')
            else:
                plt.plot(visual_x_knots, dfs[1:], '--', color='g', label='Linear DF Curve')

            plt.scatter(visual_x_knots, dfs[1:], color='red', zorder=5, label='Bootstrapped Knots')
            plt.ylabel('Discount Factor D(0, T)', fontsize=12)
            plt.title('Discount Factor Curve (Scaled Tenors)', fontsize=14, fontweight='bold')

        # 3. Apply the even spacing transformation to the axis
        plt.xticks(visual_x_milestones, milestone_labels, rotation=45, fontsize=10)
        plt.xlim(-0.5, visual_x_milestones[-1] + 0.5)

        plt.xlabel('Tenor', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.4)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def print_discount_factors(self):
        """Prints a beautifully formatted table of calculated discount factors and zero rates."""
        print("\n" + "="*50)
        print(f" DEBUG: BOOTSTRAPPED CURVE NODES (Trade Date: {self.trade_date})")
        print("="*50)
        print(f"{'Time (T)':<12} | {'Discount Factor':<18} | {'Implied Zero Rate (%)':<22}")
        print("-"*50)
        
        # Sort by time node to ensure chronological order in the console
        for t in sorted(self.discount_factors.keys()):
            df = self.discount_factors[t]
            
            # Continuous zero rate calculation: R = -ln(DF) / T
            if t == 0.0:
                zero_rate_pct = 0.0
            else:
                zero_rate_pct = (-np.log(df) / t) * 100.0
                
            print(f"{t:<12.4f} | {df:<18.6f} | {zero_rate_pct:<22.4f}%")
            
        print("="*50 + "\n")