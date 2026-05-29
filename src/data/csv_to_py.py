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
            
            required_columns = ['Instrument', 'Tenor', 'QuoteType', 'Quote']
            if not all(col in raw_data.columns for col in required_columns):
                raise ValueError(f"CSV must contain columns: {required_columns}")

            for col in ['Instrument', 'Tenor', 'QuoteType', 'Quote']:
                raw_data[col] = raw_data[col].astype(str).str.strip()

            self.curve_data = raw_data.copy()
            
            print(self.curve_data.to_string())
            
        except FileNotFoundError:
            print(f"Error: Could not find {self.data_path}")


if __name__ == "__main__":
    parser = DataParser(data_path="src/data/real-data.csv", config_path="src/data/config.json")
    
    parser.load_configuration()
    parser.load_market_data()

    print("\n--- Extracting Active Swaps for Bootstrap Engine ---")
    active_swaps = parser.get_active_instrument_slice("Swap")
    
    if active_swaps is not None and not active_swaps.empty:
        swap_tenors = active_swaps['Tenor'].tolist()
        swap_quotes = active_swaps['Quote'].tolist()
        
        print(f"Tenors to process: {swap_tenors}")
        print(f"Decimal Quotes to process: {swap_quotes}")