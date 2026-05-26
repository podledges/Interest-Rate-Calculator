def solve_forward_rate_variables(F1=None, F2=None, R=None, days=None, basis=360):
    """
    Solves for the missing variable in the implied forward rate equation:
    F1 = F2 * (1 + R * (days / basis))
    
    Provide exactly three of the four variables (F1, F2, R, days).
    R should be provided as a decimal (e.g., 0.05 for 5%).
    """
    variables_provided = sum(x is not None for x in [F1, F2, R, days])
    
    if variables_provided != 3:
        raise ValueError("Please provide exactly three of the four variables (F1, F2, R, days).")
        
    if R is None:
        # Solving for the Implied Forward Rate
        return (F1 / F2 - 1) * (basis / days)
        
    elif F1 is None:
        # Solving for the starting Discount Factor (D1)
        return F2 * (1 + R * (days / basis))
        
    elif F2 is None:
        # Solving for the ending Discount Factor (D2)
        return F1 / (1 + R * (days / basis))
        
    elif days is None:
        # Solving for the number of days between periods
        return (F1 / F2 - 1) * basis / R

# --- Example Usage ---
# Suppose the 3-month discount factor (F1) is 0.9861 and the 6-month discount factor (F2) is 0.9501.
# We want to find the forward rate (R) between those two dates (91 days apart).

# forward_rate = solve_forward_rate_variables(F1=0.9861, F2=0.9501, days=91, basis=360)
# print(f"The implied forward rate is {forward_rate * 100:.4f}%")