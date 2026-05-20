import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class SwapTimeline:
    trade_date: datetime.date
    effective_date: datetime.date
    maturity_date: datetime.date
    valuation_date: datetime.date
    
    # Optional manual inputs
    manual_forward_gap_days: Optional[int] = None
    manual_tenor_years: Optional[int] = None

    def validate_and_compile(self):
        """
        Ensure timeline matches up and user is not trolling
        SO THAT we have more customizability and flexibility in future iterations, 
        without trolling 
        """
        calculated_forward_gap = (self.effective_date - self.trade_date).days
        calculated_tenor_days = (self.maturity_date - self.effective_date).days

        if self.effective_date < self.trade_date:
            raise ValueError("Configuration Error: Effective Date cannot be earlier than Trade Date.")
            
        if self.maturity_date <= self.effective_date:
            raise ValueError("Configuration Error: Maturity Date must be after the Effective Date.")

        if self.manual_forward_gap_days is not None:
            if self.manual_forward_gap_days != calculated_forward_gap:
                raise ValueError(
                    f"Input Conflict: Manual Forward Gap ({self.manual_forward_gap_days} days) "
                    f"does not match the calendar dates ({calculated_forward_gap} days)."
                )

        print("Timeline successfully validated; no structural conflicts detected.")
        return {
            "forward_gap_days": calculated_forward_gap,
            "tenor_days": calculated_tenor_days
        }