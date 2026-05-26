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
        """Loads the rates from the CSV file and separates them by instrument."""
        try:
            # Read the CSV into a pandas DataFrame
            self.curve_data = pd.read_csv(self.data_path)
            
            # Basic validation
            required_columns = ['Instrument', 'Tenor', 'Rate']
            if not all(col in self.curve_data.columns for col in required_columns):
                raise ValueError(f"CSV must contain columns: {required_columns}")

            print("\n--- Market Data Loaded ---")
            print(self.curve_data)
            
        except FileNotFoundError:
            print(f"Error: Could not find {self.data_path}")

    def get_instrument_slice(self, instrument_type):
        """Filters the dataframe to return only specific instruments (e.g., 'Cash' or 'Swap').
            @returns the data within data.csv tied to the specified instrument type     """
        if self.curve_data.empty:
            return None
        
        # Filter the dataframe where the Instrument column matches the request
        sliced_data = self.curve_data[self.curve_data['Instrument'] == instrument_type]
        return sliced_data

if __name__ == "__main__":
    # Instantiate the parser
    parser = DataParser(data_path="data.csv", config_path="config.json")
    
    # Execute loading
    parser.load_configuration()
    parser.load_market_data()
    
    # Example of how you would extract the data to feed into your math logic later
    print("\n--- Extracting Swap Data for Bootstrapping ---")
    swap_data = parser.get_instrument_slice("Swap")
    
    # Convert the filtered data into standard Python lists for calculation
    swap_tenors = swap_data['Tenor'].tolist()
    swap_rates = swap_data['Rate'].tolist()
    
    print(f"Tenors to process: {swap_tenors}")
    print(f"Rates to process: {swap_rates}")