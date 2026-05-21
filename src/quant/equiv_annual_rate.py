def find_equivalent_annual_rate(rate: float, current_frequency: int, target_frequeny: int) -> float:
    """
    convert an interest rate from one compounding frequency to another 
    while keeping the actual annual yield (the effective return) exactly the same.
    """

    return target_frequeny * (((1+rate)/current_frequency)**(current_frequency/target_frequeny)-1)

if __name__ == "__main__":
    rate = 11.5
    current_frequency = 1
    target_frequency = 2

    semi_annual_rate = find_equivalent_annual_rate(rate, current_frequency, target_frequency)
    print(f"equivalent_rate: {semi_annual_rate:.6f}")