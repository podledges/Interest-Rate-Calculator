from quant.day_counter import calculate_year_fraction
from dateutil.relativedelta import relativedelta
from cubic_spline import CubicSplineCurve 

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
        
        # PRINT LOG FOR DEBUGGING - Check your terminal output!
        print(f"Ticker: {ticker} -> Start: {start_date} | Maturity: {maturity_date}")
        
        return start_date, maturity_date

    def _NOTparse_future_tenor(self, tenor_str):
        """
        Safely parses a ticker like 'SR3M6' or 'SR3Z7' into (start_date, maturity_date).
        """
        # Clean up any accidental whitespace
        tenor_str = tenor_str.strip()
        
        month_codes = {'H': 3, 'M': 6, 'U': 9, 'Z': 12}
        
        # Explicitly pull from the end of the string to avoid length mismatches
        month_char = tenor_str[-2]  # Second to last character (e.g., 'M')
        year_char = tenor_str[-1]   # Very last character (e.g., '6')
        
        if month_char not in month_codes:
            raise ValueError(f"Invalid month character '{month_char}' parsed from ticker '{tenor_str}'")
            
        month = month_codes[month_char]
        year = int(f"202{year_char}") # Infers 2026, 2027, 2028

        def get_third_wednesday(year, month):
            # Find all weeks that contain a Wednesday in that month
            cal = calendar.monthcalendar(year, month)
            # Filter out weeks where Wednesday (index 2) isn't 0
            wednesdays = [week[calendar.WEDNESDAY] for week in cal if week[calendar.WEDNESDAY] != 0]
            # Return the third one as a datetime.date object
            return datetime.date(year, month, wednesdays[2])
        
        start_date = get_third_wednesday(year, month)
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
        """Plots the yield curve using CubicSplineCurve over verified knots."""
        if not self.discount_factors:
            print("No curve data to display. Execute build_curve() first.")
            return

        times = np.array(sorted(self.discount_factors.keys()))
        dfs = np.array([self.discount_factors[t] for t in times])

        times_smooth = np.linspace(times.min(), times.max(), 500)

        plt.figure(figsize=(10, 6))

        if plot_type == 'zero_rate':
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
            print("ALMOST THERE!")
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