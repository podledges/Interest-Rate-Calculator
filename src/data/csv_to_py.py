import pandas as pd
import json

class DataParser:
    def __init__(self, data_path, config_path):
        self.data_path = data_path
        self.config_path = config_path
        self.settings = {}
        self.curve_data = pd.DataFrame()

    def load_configuration(self):
        """Loads the global curve settings from the JSON file."""
        try:
            with open(self.config_path, 'r') as file:
                self.settings = json.load(file)
            print("--- Configuration Loaded ---")
            for key, value in self.settings.items():
                print(f"{key}: {value}")
        except FileNotFoundError:
            print(f"Error: Could not find {self.config_path}")

    def load_market_data(self):
        """Loads rates from the CSV schema and normalizes raw quotes to uniform decimals."""
        try:
            raw_data = pd.read_csv(self.data_path)
            
            # Basic structural validation
            required_columns = ['Instrument', 'Tenor', 'QuoteType', 'Quote']
            if not all(col in raw_data.columns for col in required_columns):
                raise ValueError(f"CSV must contain columns: {required_columns}")

            # Strip any trailing/leading whitespace from text tokens
            for col in ['Instrument', 'Tenor', 'QuoteType']:
                raw_data[col] = raw_data[col].astype(str).str.strip()

            self.curve_data = raw_data.copy()
            self.curve_data['CleanedRate'] = 0.0
            
            # Convert raw quotes to standard mathematical decimals
            is_rate = self.curve_data['QuoteType'].str.upper() == 'RATE'
            is_price = self.curve_data['QuoteType'].str.upper() == 'PRICE'
            
            # Rate conversion: e.g. 3.55% -> 0.0355
            self.curve_data.loc[is_rate, 'CleanedRate'] = self.curve_data.loc[is_rate, 'Quote'] / 100.0
            
            # Price conversion: e.g. 96.33 -> 3.67% -> 0.0367
            implied_pct = 100.0 - self.curve_data.loc[is_price, 'Quote']
            self.curve_data.loc[is_price, 'CleanedRate'] = implied_pct / 100.0

            print("\n--- Market Data Loaded & Preprocessed ---")
            print(self.curve_data.to_string())
            
        except FileNotFoundError:
            print(f"Error: Could not find {self.data_path}")


if __name__ == "__main__":
    # Instantiate the updated parser
    parser = DataParser(data_path="src/data/real-data.csv", config_path="src/data/config.json")
    
    parser.load_configuration()
    
    # Mocking a quick 'TimeInYears' column insertion to test the structural filter engine
    # In production, your CurveBuilder day-counter will assign this field natively.
    parser.load_market_data()
    
    # Example execution testing if it pulls from our cleaned, non-overlapping dataset slice
    print("\n--- Extracting Active Swaps for Bootstrap Engine ---")
    active_swaps = parser.get_active_instrument_slice("Swap")
    
    if active_swaps is not None and not active_swaps.empty:
        # Extract variables using our new standardized 'CleanedRate' column
        swap_tenors = active_swaps['Tenor'].tolist()
        swap_rates = active_swaps['CleanedRate'].tolist()
        
        print(f"Tenors to process: {swap_tenors}")
        print(f"Decimal Rates to process: {swap_rates}")