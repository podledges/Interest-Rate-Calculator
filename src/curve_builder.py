import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import matplotlib.pyplot as plt
from src.quant.day_counter import calculate_year_fraction
from cubic_spline import CubicSplineCurve

class CurveBuilder:
    def __init__(self, market_data_df, config):
        self.market_data = market_data_df.copy()
        self.config = config
        
        self.trade_date = datetime.datetime.strptime(config['trade_date'], "%d-%m-%Y").date()
        self.convention = config['day_count_convention']
        self.freq = config['payment_frequency'] 
        
        # We store the exact state maps indexed by time in years
        self.grid_discount_factors = {} # {t_i: F_i}
        self.zero_rates = {0.0: 0.0} 
        self.discount_factors = [] 

    def build_curve(self):
        """Builds the curve using analytical semi-annual bootstrap (Eq 6.22)

        and linear par-rate interpolation for intermediate grid nodes.
        """
        self.market_data['MaturityDate'] = self.market_data['Tenor'].apply(self._tenor_to_date)
        self.market_data['TimeInYears'] = self.market_data['MaturityDate'].apply(
            lambda d: calculate_year_fraction(self.trade_date, d, self.convention)
        )
        
        # Sort and store explicit market benchmarks
        market_instruments = self.market_data.sort_values(by='TimeInYears').reset_index(drop=True)
        
        # Extract a dictionary of known market par rates for interpolation tasks
        market_rates = dict(zip(market_instruments['TimeInYears'], market_instruments['Rate']))
        market_times = sorted(list(market_rates.keys()))

        # 1. Handle Short-Term / Money Market instruments explicitly
        for _, row in market_instruments.iterrows():
            tenor = row['Tenor']
            t_maturity = row['TimeInYears']
            par_rate = row['Rate']
            is_short_term = tenor[-1] in ('D', 'W', 'M') or tenor == 'O/N'
            
            if is_short_term:
                mat_date = row['MaturityDate']
                tau_n = calculate_year_fraction(self.trade_date, mat_date, self.convention)
                final_df = 1.0 / (1.0 + par_rate * tau_n)
                
                self.grid_discount_factors[t_maturity] = final_df
                self.zero_rates[t_maturity] = -np.log(final_df) / t_maturity

        # 2. Construct the semi-annual swap grid (0.5Y, 1.0Y, 1.5Y, 2.0Y...) up to max maturity
        max_time = max(market_times)
        num_periods = int(round(max_time * self.freq))
        
        prev_date = self.trade_date
        grid_schedule = []
        
        # Generate our explicit bootstrapping timeline steps
        months_step = int(12 / self.freq)
        for i in range(1, num_periods + 1):
            step_date = self.trade_date + relativedelta(months=i * months_step)
            t_i = calculate_year_fraction(self.trade_date, step_date, self.convention)
            grid_schedule.append((t_i, step_date))

        # 3. Stepwise Bootstrap Loop using Equation 6.22
        for idx, (t_i, mat_date) in enumerate(grid_schedule):
            # Skip if short term data already processed it exactly
            if t_i in self.grid_discount_factors:
                continue
                
            # Step A: Find Par Swap Rate R_i (Interpolate linearly if not an explicit node - Eq 6.21)
            if t_i in market_rates:
                R_i = market_rates[t_i]
                tenor_label = market_instruments[market_instruments['TimeInYears'] == t_i]['Tenor'].values[0]
            else:
                # Equation 6.21: Linear interpolation of the par rates
                R_i = float(np.interp(t_i, market_times, [market_rates[mx] for mx in market_times]))
                tenor_label = f"{t_i:.1f}Y"

            # Step B: Compute the running summation of prior coupon fractions (Eq 6.22 numerator)
            coupon_sum = 0.0
            hist_prev_date = self.trade_date
            
            # Sum over j = 6M to i - 6M
            for j_idx in range(idx):
                t_j, current_j_date = grid_schedule[j_idx]
                alpha_j = calculate_year_fraction(hist_prev_date, current_j_date, self.convention)
                F_j = self.grid_discount_factors[t_j]
                
                coupon_sum += alpha_j * F_j
                hist_prev_date = current_j_date

            # Step C: Day-count fraction for the final payment interval
            alpha_i = calculate_year_fraction(hist_prev_date, mat_date, self.convention)
            
            # Step D: Apply Equation 6.22 explicitly
            numerator = 1.0 - R_i * coupon_sum
            denominator = 1.0 + R_i * alpha_i
            F_i = numerator / denominator
            
            # Cache state variables
            self.grid_discount_factors[t_i] = F_i
            self.zero_rates[t_i] = -np.log(F_i) / t_i
            
            self.discount_factors.append({
                'tenor': tenor_label,
                'time_in_years': t_i,
                'discount_factor': F_i,
                'zero_rate': self.zero_rates[t_i]
            })
            
        # Ensure array properties are sorted nicely for plotting operations
        self.discount_factors.sort(key=lambda x: x['time_in_years'])

    def _swap_objective_fn(self, guess_rate, mat_date, t_maturity, par_rate):
        """Calculates the mispricing error of the swap given a guessed zero rate at maturity."""
        # Temporarily stage the guessed rate in our curve grid
        self.zero_rates[t_maturity] = guess_rate
        
        schedule = self._generate_forward_schedule(mat_date)
        fixed_leg_pv = 0.0
        prev_date = self.trade_date
        
        for current_date in schedule:
            t_i = calculate_year_fraction(self.trade_date, current_date, self.convention)
            tau_i = calculate_year_fraction(prev_date, current_date, self.convention)
            
            # Interpolates intermediate points (like 1.5Y) cleanly between 1Y and the guessed 2Y rate!
            r_i = self._interpolate_zero_rate(t_i)
            df_i = np.exp(-r_i * t_i)
            
            fixed_leg_pv += par_rate * tau_i * df_i
            prev_date = current_date
            
        # Final exchange of principal benchmark value
        final_df = np.exp(-guess_rate * t_maturity)
        swap_npv = (fixed_leg_pv + final_df) - 1.0
        
        return swap_npv

    def _interpolate_zero_rate(self, t):
        """Linearly interpolates zero rates across all established or staged grid boundaries."""
        if t in self.zero_rates:
            return self.zero_rates[t]
            
        times = np.array(sorted(self.zero_rates.keys()))
        rates = np.array([self.zero_rates[time] for time in times])
        
        # Safe linear interpolation for intermediate nodes (e.g., 1.5Y, 2.5Y)
        return float(np.interp(t, times, rates))

    def _generate_forward_schedule(self, maturity_date):
        months_step = int(12 / self.freq)
        schedule = []
        current_date = maturity_date
        while current_date > self.trade_date:
            schedule.append(current_date)
            current_date -= relativedelta(months=months_step)
        schedule.reverse()
        return schedule

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

    def plot_curve(self, plot_type='zero_rate'):
        """Plots the yield curve using CubicSplineCurve over verified knots.

        plot_type options: 'zero_rate' or 'discount_factor'
        """
        if not self.discount_factors:
            print("No curve data to display. Execute build_swap_curve() first.")
            return

        times = np.array([pt['time_in_years'] for pt in self.discount_factors])
        times_smooth = np.linspace(times.min(), times.max(), 500)

        plt.figure(figsize=(10, 6))

        if plot_type == 'zero_rate':
            rates = np.array([pt['zero_rate'] * 100 for pt in self.discount_factors]) # Convert to %

            if len(times) >= 3:
                curve = CubicSplineCurve(times, rates)
                rates_smooth = curve.evaluate(times_smooth)
                plt.plot(times_smooth, rates_smooth, '-', color='b', label='Smoothed Spline Zero Curve')
            else:
                plt.plot(times, rates, '--', color='b', label='Linear Zero Curve')

            # Fixed: Moved outside the if/else check block
            plt.scatter(times, rates, color='red', zorder=5, label='Bootstrapped Knots')
            plt.ylabel('Continuous Zero Rate (%)', fontsize=12)
            plt.title('Zero-Coupon Yield Curve (Cubic Spline)', fontsize=14, fontweight='bold')

        elif plot_type == 'discount_factor':
            dfs = np.array([pt['discount_factor'] for pt in self.discount_factors])

            if len(times) >= 3:
                curve = CubicSplineCurve(times, dfs)
                dfs_smooth = curve.evaluate(times_smooth)
                plt.plot(times_smooth, dfs_smooth, '-', color='g', label='Smoothed Spline DF Curve')
            else:
                plt.plot(times, dfs, '--', color='g', label='Linear DF Curve')

            # Fixed: Moved outside the if/else check block
            plt.scatter(times, dfs, color='red', zorder=5, label='Bootstrapped Knots')
            plt.ylabel('Discount Factor D(0, T)', fontsize=12)
            plt.title('Discount Factor Curve', fontsize=14, fontweight='bold')

        # Shared canvas parameters across both visual outputs
        plt.xlabel('Time (Years)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.show()