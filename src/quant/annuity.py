


def calculate_annuity_discount_factor(discount_rate: float, num_of_payments_left: int)->float:
    #num of payment_left
    #discount_rate 
    return (1-(1+discount_rate)**num_of_payments_left)/num_of_payments_left

def calculate_annuity_present_value(regular_payment: int, num_of_payments_left:int, discount_rate: float)->float: 
    discount_factor = calculate_annuity_discount_factor(discount_rate,num_of_payments_left)
    return regular_payment * discount_factor

def calcualte_annuityPV_from_factor(factor:float, regular_payment:int)->float:
    return regular_payment * factor


