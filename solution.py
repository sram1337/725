import json
import sys

def get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config):
    per_diem_rate = 100
    
    daily_spending = total_receipts_amount / trip_duration_days if trip_duration_days > 0 else 0
    miles_per_day = miles_traveled / trip_duration_days if trip_duration_days > 0 else 0

    if trip_duration_days > 13:
        per_diem_rate = config["per_diem_rate_14_plus_days"]
    elif trip_duration_days >= 10:
        per_diem_rate = config["per_diem_rate_10_plus_days"]
    elif trip_duration_days >= 8:
        if config["apply_vacation_penalty"] and daily_spending > 150:
            per_diem_rate = 50
    
    # New, more nuanced vacation penalty
    if config.get("apply_nuanced_vacation_penalty", False):
        if trip_duration_days > 4 and daily_spending > 150 and miles_per_day < 100:
            per_diem_rate = config.get("nuanced_vacation_penalty_rate", 50)
            
    # Second-generation vacation penalty
    if config.get("zero_per_diem_vacation_penalty", False):
        if trip_duration_days > 4 and miles_per_day < 100:
            per_diem_rate = 0

    return trip_duration_days * per_diem_rate

def get_mileage_total(trip_duration_days, miles_traveled):
    primary_mileage_rate = 0.58
    secondary_mileage_rate = 0.45
    if trip_duration_days > 7:
        secondary_mileage_rate = 0.35

    if miles_traveled > 100:
        return (100 * primary_mileage_rate) + ((miles_traveled - 100) * secondary_mileage_rate)
    return miles_traveled * primary_mileage_rate

def get_receipt_total(trip_duration_days, miles_traveled, total_receipts_amount, config):
    if trip_duration_days == 1 and total_receipts_amount > 500:
        return total_receipts_amount * 0.5, 0
    if trip_duration_days == 2 and total_receipts_amount > 500:
        return total_receipts_amount * 0.6, 0

    daily_spending_limit = 0
    if trip_duration_days == 3:
        daily_spending_limit = 200
    elif 1 <= trip_duration_days <= 3:
        daily_spending_limit = 75
    elif 4 <= trip_duration_days <= 6:
        daily_spending_limit = config["receipt_cap_4_6_days"]
    elif trip_duration_days >= 7:
        daily_spending_limit = config["receipt_cap_7_plus_days"]
    
    reimbursable_receipts = total_receipts_amount
    if trip_duration_days > 0 and daily_spending_limit > 0:
        daily_spending = total_receipts_amount / trip_duration_days
        if daily_spending > daily_spending_limit:
            reimbursable_receipts = daily_spending_limit * trip_duration_days

    if reimbursable_receipts > 600:
        receipt_total = 600 * 0.8 + (reimbursable_receipts - 600) * 0.5
    elif reimbursable_receipts > 20:
        receipt_total = reimbursable_receipts * 0.8
    else:
        receipt_total = 0

    penalty = -50 if 0 < total_receipts_amount <= 20 else 0
    return receipt_total, penalty

def get_efficiency_bonus(trip_duration_days, miles_traveled):
    if trip_duration_days == 0:
        return 0
    miles_per_day = miles_traveled / trip_duration_days
    if 180 <= miles_per_day <= 220:
        return 50
    if miles_per_day < 100 or miles_per_day > 300:
        return -50
    return 0

DEFAULT_CONFIG = {
    "extreme_day_receipt_threshold": 1800,
    "extreme_day_high_receipt_pct": 0.4,
    "extreme_day_low_receipt_multiplier": 0.6,
    "per_diem_rate_10_plus_days": 75,
    "apply_vacation_penalty": False,
    "receipt_cap_4_6_days": 250,
    "receipt_cap_7_plus_days": 90,
    "per_diem_rate_14_plus_days": 50,
    "apply_nuanced_vacation_penalty": False,
    "nuanced_vacation_penalty_rate": 50,
    "zero_per_diem_vacation_penalty": False,
    "round_each_step": False,
}

def calculate_reimbursement(trip_duration_days, miles_traveled, total_receipts_amount, debug=False, config=DEFAULT_CONFIG):
    path = "NORMAL"

    # Special case for extreme 1-day trips
    if trip_duration_days == 1 and miles_traveled > 800:
        if total_receipts_amount > config["extreme_day_receipt_threshold"]:
            path = "SPECIAL_EXTREME_ONE_DAY_HIGH_RECEIPT"
            computed_total = round(total_receipts_amount * config["extreme_day_high_receipt_pct"], 2)
        else:
            path = "SPECIAL_EXTREME_ONE_DAY_LOW_RECEIPT"
            computed_total = round((miles_traveled + total_receipts_amount) * config["extreme_day_low_receipt_multiplier"], 2)
        
        if debug:
            return {
                "path": path, "per_diem": 0, "mileage": 0, "receipts$": computed_total, "penalty": 0, "eff_bonus": 0,
                "grand": computed_total
            }
        return computed_total

    per_diem_total = get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config)
    mileage_total = get_mileage_total(trip_duration_days, miles_traveled)
    receipt_total, penalty = get_receipt_total(trip_duration_days, miles_traveled, total_receipts_amount, config)
    efficiency_bonus = get_efficiency_bonus(trip_duration_days, miles_traveled)

    if config.get("round_each_step", False):
        per_diem_total = round(per_diem_total, 2)
        mileage_total = round(mileage_total, 2)
        receipt_total = round(receipt_total, 2)

    # Determine path for debugging
    if get_receipt_total.__code__.co_varnames[0] != 'self': # crude way to check if it's a special receipt case
         if trip_duration_days == 1 and total_receipts_amount > 500:
             path = "SPECIAL_ONE_DAY_HIGH_RECEIPT"
         elif trip_duration_days == 2 and total_receipts_amount > 500:
             path = "SPECIAL_TWO_DAY_HIGH_RECEIPT"


    computed_total = round(per_diem_total + mileage_total + receipt_total + penalty + efficiency_bonus, 2)

    if debug:
        return {
            "path": path,
            "per_diem": per_diem_total,
            "mileage": mileage_total,
            "receipts$": receipt_total,
            "penalty": penalty,
            "eff_bonus": efficiency_bonus,
            "grand": computed_total
        }

    return computed_total

if __name__ == '__main__':
    # This part of the script is now for testing and analysis
    if len(sys.argv) == 4:
        # Running from command line for eval.sh
        trip_duration_days = int(sys.argv[1])
        miles_traveled = int(sys.argv[2])
        total_receipts_amount = float(sys.argv[3])
        
        reimbursement = calculate_reimbursement(
            trip_duration_days,
            miles_traveled,
            total_receipts_amount
        )
        print(reimbursement)
    else:
        # Running for testing with public_cases.json
        with open('public_cases.json', 'r') as f:
            cases = json.load(f)
        
        errors = []
        
        for case in cases:
            inputs = case['input']
            expected_output = case['expected_output']
            
            # Get the debug output
            debug_info = calculate_reimbursement(
                inputs['trip_duration_days'],
                inputs['miles_traveled'],
                inputs['total_receipts_amount'],
                debug=True
            )
            
            calculated_output = debug_info['grand']
            error = abs(calculated_output - expected_output)
            errors.append({'input': inputs, 'expected': expected_output, 'debug': debug_info, 'error': error})
            
        average_error = sum(e['error'] for e in errors) / len(cases)
        print(f"Average Error: {average_error:.2f}\n")

        errors.sort(key=lambda x: x['error'], reverse=True)
        
        print("Top 5 Worst Errors:")
        for i in range(min(5, len(errors))):
            e = errors[i]
            print(f"Input: {e['input']}, Expected: {e['expected']:.2f}, Error: {e['error']:.2f}")
            print(f"  Debug Info: {e['debug']}")
            print("-" * 20) 