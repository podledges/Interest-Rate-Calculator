import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd

class DiscountCurveBuilder:
    def __init__(self, market_data_df, trade_date_str, convention='ACT/365', freq=2):
        self.market_data = market_data_df.copy()
        self.trade_date = datetime.datetime.strptime(trade_date_str, "%d-%m-%Y").date()
        self.convention = convention
        self.freq = freq  # 1 for Annual, 2 for Semi-Annual, 4 for Quarterly
        
        # Core storage: Maps a year fraction (float) to its solved Discount Factor (float)
        # Seed the boundary condition: D(0, 0) = 1.0
        self.discount_factors = {0.0: 1.0}

    def build_discount_factors(self):
        """Sequential bootstrap to calculate exact maturity discount factors."""
        # 1. Parse and sort instruments by maturity
        swaps = self.market_data[self.market_data['Instrument'] == 'Swap'].copy()
        swaps['MaturityDate'] = swaps['Tenor'].apply(self._tenor_to_date)
        swaps['TimeInYears'] = swaps['MaturityDate'].apply(
            lambda d: self._calculate_year_fraction(self.trade_date, d)
        )
        swaps = swaps.sort_values(by='TimeInYears').reset_index(drop=True)

        print(f"Bootstrapping starting from Trade Date: {self.trade_date}")
        print("-" * 65)
        print(f"{'Tenor':<8}{'Maturity':<12}{'Time (Y)':<10}{'Par Rate (%)':<15}{'Discount Factor':<15}")
        print("-" * 65)

        # 2. Sequential Bootstrap Loop
        for _, row in swaps.iterrows():
            mat_date = row['MaturityDate']
            t_maturity = row['TimeInYears']
            par_rate = row['Rate']
            
            # Generate the exact payment schedule for THIS swap
            schedule = self._generate_forward_schedule(mat_date)
            
            running_coupon_pv = 0.0
            prev_date = self.trade_date
            
            # Sum up the PV of all intermediate coupons (excluding the final maturity payment)
            for current_date in schedule[:-1]:
                t_i = self._calculate_year_fraction(self.trade_date, current_date)
                tau_i = self._calculate_year_fraction(prev_date, current_date)
                
                # Look up the intermediate discount factor. 
                # If it's not a direct market knot, we use a basic linear interpolation of surrounding DFs.
                df_i = self._get_discount_factor(t_i)
                
                running_coupon_pv += tau_i * df_i
                prev_date = current_date
                
            # Final period accrual fraction
            tau_n = self._calculate_year_fraction(prev_date, mat_date)
            
            # Textbook analytic solution for the final discount factor
            numerator = 1.0 - (par_rate * running_coupon_pv)
            denominator = 1.0 + (par_rate * tau_n)
            
            final_df = numerator / denominator
            
            # Save the solved market knot
            self.discount_factors[t_maturity] = final_df
            
            print(f"{row['Tenor']:<8}{str(mat_date):<12}{t_maturity:<10.4f}{par_rate*100:<15.4f}{final_df:<15.6f}")

    def _get_discount_factor(self, t):
        """Helper to return an exact or linearly interpolated discount factor."""
        if t in self.discount_factors:
            return self.discount_factors[t]
            
        # Separate solved knots to find bounding points for linear interpolation
        sorted_times = np.array(sorted(self.discount_factors.keys()))
        sorted_dfs = np.array([self.discount_factors[time] for time in sorted_times])
        
        # Basic linear interpolation on discount factors for intermediate coupon dates
        return float(np.interp(t, sorted_times, sorted_dfs))

    def _generate_forward_schedule(self, maturity_date):
        """Generates unadjusted coupon payment dates moving forward from trade date."""
        months_step = int(12 / self.freq)
        schedule = []
        current_date = maturity_date
        
        while current_date > self.trade_date:
            schedule.append(current_date)
            current_date -= relativedelta(months=months_step)
            
        schedule.reverse()
        return schedule

    def _calculate_year_fraction(self, d1, d2):
        """Standard ACT/365 day count fraction helper."""
        return (d2 - d1).days / 365.0
    
    from dateutil.relativedelta import relativedelta

    def _tenor_to_date(self, tenor_str):
        """Converts a standard market tenor string into an exact maturity date."""
        tenor_str = tenor_str.upper().strip()
        
        # 1. Handle short-term money market conventions
        if tenor_str in ('O/N', 'OVERNIGHT'):
            return self.trade_date + relativedelta(days=1)
        if tenor_str in ('S/N', 'SPOT'):
            return self.trade_date + relativedelta(days=2)
            
        # 2. Extract value and unit identifier
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
                raise ValueError(f"Unknown tenor unit rule: {unit}")
                
        except ValueError:
            raise ValueError(f"Could not parse market tenor string: '{tenor_str}'")
        
import io
import pandas as pd

# Raw market data string
raw_data = """Instrument,Tenor,Rate
Swap,O/N,0.1425
Swap,1W,0.1475
Swap,1M,0.1500
Swap,2M,0.15125
Swap,3M,0.1515625
Swap,6M,0.15375
Swap,1Y,0.1555
Swap,2Y,0.1425
Swap,3Y,0.1395
Swap,4Y,0.1385
Swap,5Y,0.1375
Swap,7Y,0.1355
Swap,10Y,0.1310"""

# Read into a clean pandas DataFrame
market_data_df = pd.read_csv(io.StringIO(raw_data))

# Clean up whitespace if any exists
market_data_df['Tenor'] = market_data_df['Tenor'].str.strip()
market_data_df['Instrument'] = market_data_df['Instrument'].str.strip()

# Display the formatted DataFrame structure
print(market_data_df)

# Run builder
builder = DiscountCurveBuilder(market_data_df, trade_date_str="01-01-2026", freq=2)
builder.build_discount_factors()